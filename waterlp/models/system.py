import os
import json
from attrdict import AttrDict
import boto3
from datetime import datetime as dt
from tqdm import tqdm

from waterlp.models.pywr2 import PywrModel
from waterlp.models.evaluator import Evaluator
from waterlp.models.base.utilities.converter import convert

INITIAL_STORAGE_ATTRS = [
    ('reservoir', 'Initial Storage'),
    ('groundwater', 'Initial Storage')
]


def perturb(val, variation):
    # NB: this is made explicit to avoid using exec
    operator = variation['operator']
    value = variation['value']
    if operator == 'multiply':
        if type(val) == dict:
            for c, vals in val.items():
                for i, v in vals.items():
                    if val[c][i] is not None:
                        val[c][i] *= value
        else:
            return val * value
    elif operator == 'add':
        if type(val) == dict:
            for c, vals in val.items():
                for i, v in vals.items():
                    if val[c][i] is not None:
                        val[c][i] = value

        else:
            return val + value
    else:
        return val


def add_subblocks(self, values, attr_name):
    subblocks = self.default_subblocks
    nsubblocks = self.nsubblocks

    new_values = {}

    if attr_name in self.demandParams:
        new_vals = {}
        try:
            for block in values:
                for d, v in values[block].items():
                    new_vals[d] = v / nsubblocks
                for i, subblock in enumerate(subblocks):
                    new_values[(block, subblock)] = new_vals
        except:
            raise

    elif attr_name in self.valueParams:
        try:
            for block in values:
                for i, subblock in enumerate(subblocks):
                    new_vals = {}
                    for d, v in values[block].items():
                        # new_vals[d] = v + (1 - sqrt((nsubblocks - i) / nsubblocks))
                        new_vals[d] = v - 1 + ((nsubblocks - i) / nsubblocks) ** 2
                    new_values[(block, subblock)] = new_vals
        except:
            raise

    return new_values


class WaterSystem(object):

    def __init__(self, conn, name, network, all_scenarios, template, args, date_format='iso',
                 session=None, reporter=None, scenario=None):

        self.storage = network.layout.get('storage')
        self.bucket_name = os.environ.get('AWS_S3_BUCKET')

        self.conn = conn
        self.session = session
        self.name = name
        self.scenario = scenario
        self.template = template
        self.reporter = reporter
        self.args = args
        self.date_format = date_format
        self.storage_scale = 1
        self.storage_unit = 'hm^3'

        self.scenarios = {s.name: s for s in all_scenarios}
        self.scenarios_by_id = {s.id: s for s in all_scenarios}

        self.foresight = args.foresight  # pending further development

        # extract info about nodes & links
        self.network = network
        self.resources = {}
        self.ttypes = {}
        self.res_tattrs = {}

        self.initial_volumes = {}
        self.constants = {}
        self.descriptors = {}
        self.parameters = {}
        self.urls = {}
        self.block_params = []
        self.blocks = {'node': {}, 'link': {}, 'network': {}}
        self.res_scens = {}

        self.params = {}  # to be defined later
        self.nparams = 0
        self.nvars = 0

        self.attrs_to_save = []

        self.log_dir = 'log/{run_name}'.format(run_name=self.args.run_name)

        ttypeattrs = {}
        rtypeattrs = {}

        for tt in template.types:
            resource_type = tt.resource_type.lower()  # i.e., node, link, network
            self.ttypes[(resource_type, tt['name'])] = []

            # use typeattrs to track variables/parameters
            ttypeattrs[(resource_type, tt['name'])] = tt.typeattrs

        # organize basic network information
        # features['networks'] = [network]

        def get_resource_attributes(resource, resource_type):
            rtypes = [rt for rt in resource.types if rt.template_id == template.id]
            if not rtypes:
                return
            elif resource_type != 'network' and len(rtypes) > 1:
                raise Exception("More than one type for {} {}".format(resource_type, resource['name']))
            else:
                rt = rtypes[0]  # network type should be the first one

            idx = (resource_type, resource.id)
            resource['type'] = rt
            self.resources[idx] = resource

            # a dictionary of template_type to resource
            self.ttypes[(resource_type, rt['name'])].append(idx)
            # self.res_ttypes[idx] = rt['name']

            tattrs = {ta.attr_id: ta for ta in ttypeattrs[(resource_type, rt['name'])]}

            # general resource attribute information
            for ra in resource.attributes:
                if ra.attr_id not in tattrs:
                    continue
                tattr = tattrs[ra.attr_id]
                self.res_tattrs[ra.id] = tattr

                if tattr.is_var == 'Y' and tattr.properties.get('save', False):
                    self.attrs_to_save.append((resource_type, resource.id, tattr['attr_id']))

                if ra.attr_is_var == 'N' and not args.suppress_input:
                    self.nparams += 1
                else:
                    self.nvars += 1

        get_resource_attributes(network, 'network')
        for node in network.nodes:
            get_resource_attributes(node, 'node')
        for link in network.links:
            get_resource_attributes(link, 'link')

        # initialize dictionary of parameters
        # self.scalars = {feature_type: {} for feature_type in ['node', 'link', 'net']}

        self.ra_node = {ra.id: node.id for node in network.nodes for ra in node.attributes}  # res_attr to node lookup
        self.ra_link = {ra.id: link.id for link in network.links for ra in link.attributes}  # res_attr to link lookup

    def create_exception(self, key, message):

        resource_type, resource_id, attr_id = key.split('/')
        resource_id = int(resource_id)
        attr_id = int(attr_id)
        attr_name = self.conn.tattrs.get((resource_type, resource_id, attr_id), {}).get('attr_name',
                                                                                        'unknown attribute')
        if resource_type == 'network':
            resource_name = self.network['name']
        else:
            resource_name = self.resources.get((resource_type, resource_id), {}).get('name', 'unknown resource')

        msg = 'Error calculating {attr} at {rtype} {res}:\n\n{exc}'.format(
            attr=attr_name,
            rtype=resource_type,
            res=resource_name,
            exc=message
        )

        print(msg)

        return Exception(msg)

    def initialize_time_steps(self):
        # initialize time steps and foresight periods

        time_settings = {
            'start': self.scenario.start_time,
            'end': self.scenario.end_time,
            'span': self.scenario.time_step,
        }

        network_storage = self.conn.network.layout.get('storage')

        if network_storage.location == 'AmazonS3':
            network_folder = self.conn.network.layout.get('storage', {}).get('folder')
            files_path = network_folder
        else:
            files_path = None

        debug_ts = self.args.debug_ts if self.args.debug else None
        self.evaluator = Evaluator(self.conn, time_settings=time_settings, files_path=files_path,
                                   date_format=self.date_format, debug_ts=debug_ts,
                                   debug_start=self.args.debug_start)

        self.timesteps = self.evaluator.timesteps
        self.dates = self.evaluator.dates
        self.dates_as_string = self.evaluator.dates_as_string

        # timestep deltas
        self.tsdeltas = {}

        # use the dates in evaluator because we've already incurred the expense of parsing the date.
        self.tsdeltas = dict((self.dates_as_string[i], self.evaluator.dates[i + 1] - ts) for i, ts in
                             enumerate(self.evaluator.dates[:-1]))
        self.tsdeltas[self.evaluator.dates_as_string[-1]] = self.tsdeltas[
            self.evaluator.dates_as_string[-2]]  # TODO: fix this

        # NB: to be as efficient as possible within run loops, we should keep as much out of the loops as possible
        self.nruns = len(self.dates)
        if self.foresight == 'perfect':
            self.foresight_periods = len(self.dates)
            self.save_periods = self.foresight_periods
            self.nruns = 1
        elif self.foresight == 'zero':
            self.foresight_periods = 1
            self.save_periods = 1
        self.ts_idx = range(self.foresight_periods)

    def collect_source_data(self):
        """
        This does some pre-processing to organize data for more efficient lookup later.
        """

        tsi = 0
        tsf = self.foresight_periods

        self.evaluator.block_params = self.block_params

        nsubblocks = 1
        self.default_subblocks = list(range(nsubblocks))

        N = len(self.dates)

        # collect source data
        # Importantly, this routine overwrites parent scenario data with child scenario data
        resource_scenarios = {}
        for source_id in self.scenario.source_ids:

            self.evaluator.scenario_id = source_id

            source = self.scenario.source_scenarios[source_id]

            for rs in source.resourcescenarios:

                if rs.resource_attr_id not in self.res_tattrs:
                    continue  # this is for a different resource type

                # get identifiers
                if rs.resource_attr_id in self.ra_node:
                    resource_type = 'node'
                    resource_id = self.ra_node[rs.resource_attr_id]
                elif rs.resource_attr_id in self.ra_link:
                    resource_type = 'link'
                    resource_id = self.ra_link[rs.resource_attr_id]
                else:
                    resource_type = 'network'
                    resource_id = self.network.id

                key = '{}/{}/{}'.format(resource_type, resource_id, rs.attr_id)
                resource_scenarios[key] = rs

        # collect/evaluate source data
        print("[*] Collecting source data")
        cnt = 0
        # for source_id in self.scenario.source_ids:

        # self.evaluator.scenario_id = source_id

        # source = self.scenario.source_scenarios[source_id]

        print("[*] Collecting data")
        for res_attr_idx in tqdm(resource_scenarios, ncols=80, disable=not self.args.verbose):
            rs = resource_scenarios[res_attr_idx]
            cnt += 1

            # get identifiers
            if rs.resource_attr_id in self.ra_node:
                resource_type = 'node'
                resource_id = self.ra_node[rs.resource_attr_id]
            elif rs.resource_attr_id in self.ra_link:
                resource_type = 'link'
                resource_id = self.ra_link[rs.resource_attr_id]
            else:
                resource_type = 'network'
                resource_id = self.network.id
            res_idx = (resource_type, resource_id)

            resource = self.resources.get(res_idx)
            resource_name = resource['name']

            # key = '{}/{}/{}'.format(resource_type, resource_id, rs.attr_id)

            # get attr name
            attr_id = rs.attr_id
            tattr = self.conn.tattrs[(resource_type, resource_id, attr_id)]
            if not tattr:
                continue

            # store the resource scenario value for future lookup

            intermediary = tattr['properties'].get('intermediary', False)
            is_var = tattr['is_var'] == 'Y'

            # non-intermediary outputs should not be pre-processed at all
            if is_var and not intermediary:
                continue

            # load the metadata
            metadata = json.loads(rs.value.metadata)

            # identify as function or not
            input_method = metadata.get('input_method', 'native')
            is_function = metadata.get('use_function', 'N') == 'Y' or input_method == 'function'

            # get data type
            data_type = rs.value.type

            if data_type == 'descriptor':
                continue # TODO: resolve this somehow

            # update data type
            self.res_tattrs[rs.resource_attr_id]['data_type'] = data_type

            # default blocks

            type_name = self.resources[(resource_type, resource_id)]['type']['name']
            idx = (resource_type, resource_id, attr_id)

            value = None
            if not (is_var and is_function):
                if input_method in ['module', 'controlcurve']:
                    data = metadata.get('data')
                    if not data:
                        continue
                    value = json.loads(data)
                else:
                    value = self.evaluator.eval_data(
                        value=rs.value,
                        fill_value=0,
                        date_format=self.date_format,
                        flavor='native',
                    )

            if not is_var and (value is None or (type(value) == str and not value)):
                continue

            # TODO: add generic unit conversion utility here
            dimension = rs.value.dimension
            if resource_type == 'network':
                res_attr_name = tattr['attr_name']
            else:
                res_attr_name = '{}/{}/{}'.format(resource_type, resource['name'], tattr['attr_name'])

            is_scalar = data_type == 'scalar' or type(value) in [int, float]

            if data_type == 'scalar':
                try:
                    value = float(value)
                except:
                    raise Exception("Could not convert scalar")

            if (type_name.lower(), tattr['attr_name']) in INITIAL_STORAGE_ATTRS:
                self.initial_volumes[idx] = value

            elif is_scalar:
                self.parameters[idx] = {
                    'type': 'variable',
                    'value': {
                        'name': res_attr_name,
                        'pywr_type': 'constant',
                        'value': value
                    }
                }

            elif is_function:
                self.parameters[idx] = {
                    'type': 'parameter',
                    'value': {
                        'name': res_attr_name,
                        'code': value
                    }
                }

            elif input_method == 'module':
                self.parameters[idx] = {
                    'type': 'module',
                    'value': value
                }

            elif input_method == 'controlcurve':
                self.parameters[idx] = {
                    'type': 'controlcurve',
                    'value': {
                        'name': res_attr_name,
                        'data': value
                    }
                }
            #
            # elif data_type == 'descriptor':  # this could change later
            #     self.parameters[idx] = {
            #         'type': 'descriptor',
            #         'value': {
            #             'name': res_attr_name,
            #             'value': value
            #         }
            #     }

            elif data_type == 'timeseries':
                values = value
                self.parameters[idx] = {
                    'type': 'variable',
                    'value': {
                        'name': '{}_{}'.format(tattr['attr_name'], rs['dataset_id']),
                        'data_type': data_type,
                        'value': values,
                    }
                }

        return

    def initialize(self, supersubscenario):
        """A wrapper for all initialization steps."""

        # prepare parameters
        self.prepare_params()

        # set up subscenario
        self.setup_subscenario(supersubscenario)

        current_dates_as_string = self.dates_as_string[:self.foresight_periods]
        step = self.dates[0].day

        # set up the time steps
        if self.scenario.time_step == 'day':
            start = self.scenario.start_time
            end = self.scenario.end_time
            step = 1
        else:
            start = current_dates_as_string[0]
            end = current_dates_as_string[-1]
            step = step

        # set up initial values
        initial_volumes = {}
        constants = {}
        variables = {}

        def convert_values(source, dest, dest_key='res_attr_idx'):
            for res_attr_idx in list(source):
                resource_type, resource_id, attr_id = res_attr_idx
                type_name = self.resources[(resource_type, resource_id)]['type']['name']
                param = self.params[(resource_type, type_name, attr_id)]
                scale = param['scale']
                unit = param['unit']
                dimension = param['dimension']
                value = source.pop(res_attr_idx)
                if dimension == 'Volumetric flow rate':
                    val = convert(value, unit, 'hm^3 day^-1', scale_in=scale)
                elif dimension == 'Volume':
                    val = convert(value, unit, 'hm^3', scale_in=scale)
                else:
                    val = value
                if dest_key == 'res_attr_idx':
                    dest[res_attr_idx] = val
                elif dest_key == 'resource_id':
                    dest[resource_id] = val

        convert_values(self.constants, constants)
        convert_values(self.initial_volumes, initial_volumes, dest_key='resource_id')

        # for res_attr_idx in list(self.variables):
        #     if self.variables[res_attr_idx].get('is_ready'):
        #         variables[res_attr_idx] = self.variables.pop(res_attr_idx)

        self.model = PywrModel(
            network=self.network,
            template=self.template,
            tattrs=self.conn.tattrs,
            start=start,
            end=end,
            step=step,
            initial_volumes=initial_volumes,
            constants=constants,
            parameters=self.parameters,
        )

        return

    def prepare_params(self):
        """
        Declare parameters, based on the template type.
        The result is a dictionary of all parameters for later use and extension.
        """

        for ttype in self.template.types:

            resource_type = ttype['resource_type']

            # if resource_type == 'NETWORK':
            #     continue

            for tattr in ttype.typeattrs:

                # data_type = tattr['data_type']

                # create a unique parameter index
                attr_id = tattr['attr_id']
                type_name = ttype['name']
                tattr_idx = (resource_type.lower(), type_name, attr_id)
                if tattr_idx not in self.params:
                    param = AttrDict(tattr)
                    param.update(param.properties)
                    param.update(
                        scale=param.get('scale', 1),
                        unit=param.get('unit'),
                        intermediary=param.get('intermediary', False),
                        resource_type=resource_type.lower()
                    )
                    del param['properties']
                    self.params[tattr_idx] = param

                    if tattr['attr_name'] == 'Initial Storage':
                        self.storage_scale = param.get('scale', 1)
                        self.storage_unit = param.unit

    def setup_subscenario(self, supersubscenario):
        """
        Add variation to all resource attributes as needed.
        There are two variations: option variations and scenario variations.
        If there is any conflict, scenario variations will replace option variations.
        """

        variation_sets = supersubscenario.get('variation_sets')

        self.metadata = {'number': supersubscenario.get('id'), 'variation_sets': {}}
        for i, variation_set in enumerate(variation_sets):
            vs = []
            for (resource_type, resource_id, attr_id), value in variation_set['variations'].items():
                tattr = self.conn.tattrs.get((resource_type, resource_id, attr_id))
                resource_name = self.resources.get((resource_type, resource_id), {}).get('name', 'unknown resource')

                vs.append({
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'resource_name': resource_name,
                    'attr_id': attr_id,
                    'attr_name': tattr['attr_name'],
                    'variation': value
                })
            scenario_type = 'option' if i == 0 else 'scenario'
            self.metadata['variation_sets'][scenario_type] = {
                'parent_id': variation_set['parent_id'],
                'variations': vs
            }

        for variation_set in variation_sets:
            for key, variation in variation_set['variations'].items():
                (resource_type, resource_id, attr_id) = key
                tattr = self.conn.tattrs[key]
                attr_id = tattr['attr_id']

                # at this point, timeseries have not been assigned to variables, so these are mutually exclusive
                # the order here shouldn't matter
                res_attr_idx = (resource_type, resource_id, attr_id)
                constant = self.constants.get(res_attr_idx)
                parameter = self.parameters.get(res_attr_idx)

                if constant:
                    self.constants[res_attr_idx] = perturb(self.constants[res_attr_idx], variation)

                elif parameter and parameter['type'] == 'variable':

                    if not parameter.get('function'):  # functions will be handled by the evaluator
                        self.parameter[res_attr_idx]['value']['values'] \
                            = perturb(self.variables[res_attr_idx]['value']['values'], variation)

                else:  # we need to add the variable to account for the variation
                    data_type = tattr['data_type']
                    if data_type == 'scalar':
                        self.constants[res_attr_idx] = perturb(0, variation)
                    elif data_type == 'descriptor':
                        self.descriptors[res_attr_idx] = perturb(0, variation)
                    elif data_type == 'timeseries':

                        self.parameters[res_attr_idx].update(
                            value={
                                'values': perturb(self.evaluator.default_timeseries.copy(), variation),
                                'dimension': tattr['dimension']
                            }
                        )

    def step(self):
        self.model.step()

    def run(self):
        self.model.run()

    def finish(self):
        self.save_results()
        self.model.finish()

    def cleanup(self):
        self.model.cleanup()

    def save_logs(self):

        for filename in ['pywr_glpk_debug.lp', 'pywr_glpk_debug.mps']:
            if os.path.exists(filename):
                with open(filename, 'r') as file:
                    key = '{network_folder}/{log_dir}/{filename}'.format(
                        network_folder=self.storage.folder,
                        log_dir=self.log_dir,
                        filename=filename
                    )
                    content = file.read()
                    self.save_to_file(key, content)
            else:
                return None

    def save_to_file(self, key, content):
        s3 = boto3.client('s3')
        s3.put_object(Body=content, Bucket=self.bucket_name, Key=key)

    def save_results(self, error=False):

        print('[*] Saving data')

        if self.scenario.reporter:
            self.scenario.reporter.report(action='save', saved=0)

        self.scenario.scenario_id = self.scenario.result_scenario['id']

        if self.scenario.destination == 'source':
            self.save_results_to_source()
        elif self.scenario.destination == 's3':
            self.save_results_to_csv('s3')
        elif self.scenario.destination == 'local':
            self.save_results_to_csv('local')

    def save_results_to_source(self):

        result_scenario = self.scenario.result_scenario

        # save variable data to database
        res_scens = []
        mb = 0
        res_names = {}

        try:

            # =============
            # write results
            # =============

            _df = self.model.model.to_dataframe()
            dt = self.model.model.timestepper.current.datetime
            df = _df[_df.index <= dt]
            cols = df.columns
            ncols = len(cols)

            if not ncols:
                self.scenario.reporter.report(
                    action='error',
                    message="ERROR: No results have been reported. The model might not have run."
                )

            def dump_results(res_scens):
                result_scenario['resourcescenarios'] = res_scens
                result_scenario['layout'].update({
                    'modified_date': dt.now().isoformat(' '),
                    'modified_by': self.args.user_id
                })
                resp = self.conn.dump_results(result_scenario)

                if 'id' not in resp:
                    raise Exception('Error saving data')

            n = 0

            for col in tqdm(cols, ncols=80, leave=False, disable=not self.args.verbose):

                n += 1
                res_attr_idx = col[0]
                resource_type, resource_name, attr_name_lower = res_attr_idx.split('/')

                tattr = self.conn.tattr_lookup.get(res_attr_idx)
                res_attr_id = self.conn.res_attr_lookup.get(res_attr_idx)

                if not (res_attr_id and tattr and tattr['properties'].get('save')):
                    continue

                # type_name = self.resources[(resource_type, resource_id)]['type']['name']
                # param = self.params.get((resource_type, type_name, attr_id))
                # if not param:
                #     continue  # it's probably an internal variable/parameter

                # resource_name = self.conn.raid_to_res_name[res_attr_id]
                attr_name = tattr['attr_name']

                # define the dataset value
                data_type = tattr['data_type']
                try:

                    if 'timeseries' in data_type:
                        content = df[res_attr_idx].to_json(date_format='iso')
                    else:
                        content = str(df[res_attr_idx])
                except:
                    print('Failed to prepare: {}'.format(attr_name))
                    continue

                if resource_type == 'network':
                    res_scen_name = '{} - {} [{}]'.format(self.network.name, tattr['attr_name'], self.scenario.name)
                else:
                    res_scen_name = '{} - {} - {} [{}]'.format(self.network.name,
                                                               resource_name,
                                                               attr_name,
                                                               self.scenario.name)

                if tattr['dimension'] == 'Temperature':
                    continue  # TODO: fix this!!!

                rs = {
                    'resource_attr_id': res_attr_id,
                    'value': {
                        'type': tattr['data_type'],
                        'name': res_scen_name,
                        'unit': tattr['unit'],
                        'dimension': tattr['dimension'],
                        'value': content
                    }
                }
                res_scens.append(rs)
                mb += len(content.encode()) * 1.1 / 1e6  # large factor of safety

                if mb > 10 or n % 100 == 0:
                    dump_results(res_scens[:-1])

                    # purge just-uploaded scenarios
                    res_scens = res_scens[-1:]
                    mb = 0

                    self.scenario.reporter.report(action='save', saved=round(n / ncols * 100))

            # upload the last remaining resource scenarios
            dump_results(res_scens)
            self.scenario.reporter.report(action='save', force=True, saved=round(n / ncols * 100))

            # self.scenario.result_scenario_id = result_scenario['id']

        except:
            msg = 'ERROR: Results could not be saved.'
            # self.logd.info(msg)
            if self.scenario.reporter:
                self.scenario.reporter.report(action='error', message=msg)
            raise

    def save_results_to_csv(self, dest):

        s3 = None
        if dest == 's3':
            s3 = boto3.client('s3')

        human_readable = self.args.human_readable

        if len(self.scenario.base_ids) == 1:
            o = s = self.scenario.base_ids[0]
        else:
            o, s = self.scenario.base_ids

        if human_readable:
            variation_name = '{{:0{}}}' \
                .format(len(str(self.scenario.subscenario_count))) \
                .format(self.metadata['number'])
            variation_sets = self.metadata['variation_sets']
            for scope in variation_sets:
                for variation in variation_sets[scope]['variations']:
                    variation_name += '__{}={}'.format(
                        variation['resource_name'][:1],
                        variation['variation']['value']
                    )

        else:
            variation_name = self.metadata['number']

        base_path = '{scenario_base_path}/{variation}'.format(
            scenario_base_path=self.scenario.base_path,
            variation=variation_name
        )

        if dest == 'local':
            home_folder = os.getenv('HOME')
            base_path = os.path.join(home_folder, '.openagua', base_path)
            if not os.path.exists(base_path):
                os.makedirs(base_path)

        try:

            # ==============
            # write metadata
            # ==============

            metadata = json.dumps(self.metadata, sort_keys=True, indent=4, separators=(',', ': '))

            if dest == 's3':
                s3.put_object(Body=metadata.encode(), Bucket=self.bucket_name, Key=base_path + '/metadata.json')
            elif dest == 'local':
                file_path = os.path.join(base_path, 'metadata.json')
                with open(file_path, 'w') as outfile:
                    json.dump(self.metadata, outfile, sort_keys=True, indent=4, separators=(',', ': '))

            # =============
            # write results
            # =============

            df = self.model.model.to_dataframe()
            n = 0
            ncols = len(df.columns)
            path = base_path + '/{resource_type}/{resource_subtype}/{resource_id}'
            cols = df.columns

            for col in tqdm(cols, ncols=80, leave=False, disable=not self.args.verbose):

                n += 1

                res_attr_idx = col[0]
                resource_type, resource_id, attr_id = res_attr_idx.split('/')
                resource_id = int(resource_id)
                attr_id = int(attr_id)

                idx = (resource_type, resource_id, attr_id)

                tattr = self.conn.tattrs.get(idx)
                res_attr_id = self.conn.res_attr_lookup.get(idx)

                if not (res_attr_id and tattr and tattr['properties'].get('save')):
                    continue

                # prepare data

                # define the dataset value
                data_type = tattr['data_type']
                attr_name = tattr['attr_name']
                try:
                    if 'timeseries' in data_type:
                        content = df[res_attr_idx].to_csv()
                    else:
                        content = str(df[res_attr_idx].value())
                except:
                    print('Failed to prepare: {}'.format(attr_name))
                    continue

                if content:
                    ttype = self.conn.types.get((resource_type, resource_id))
                    if human_readable:
                        resource_name = self.conn.raid_to_res_name[res_attr_id]
                        key = path.format(
                            resource_type=resource_type,
                            resource_subtype=ttype['name'],
                            resource_id=resource_name,
                        )
                    else:
                        key = path.format(
                            resource_type=resource_type,
                            resource_subtype=ttype['id'],
                            resource_id=resource_id,
                        )

                    filename = '{attr_id}.csv'.format(attr_id=attr_name if human_readable else attr_id)
                    if dest == 's3':
                        key = os.path.join(key, filename)
                        s3.put_object(Body=content.encode(), Bucket=self.bucket_name, Key=key)
                    else:
                        file_path = os.path.join(base_path, key)
                        if not os.path.exists(file_path):
                            os.makedirs(file_path)
                        with open(os.path.join(file_path, filename), 'wb') as outfile:
                            outfile.write(content.encode())

                if n % 10 == 0 or n == ncols:
                    if self.scenario.reporter:
                        self.scenario.reporter.report(action='save', saved=round(n / ncols * 100))

        except:
            msg = 'ERROR: Results could not be saved.'
            # self.logd.info(msg)
            if self.scenario.reporter:
                self.scenario.reporter.report(action='error', message=msg)
            raise
