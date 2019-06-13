import os
import sys
import json
from importlib import import_module
import boto3
from tempfile import mkdtemp
from shutil import rmtree, copytree
import pandas

from pywr.core import Model

from .utils import resource_name, clean_parameter_name, create_policy, create_variable, create_control_curve

oa_attr_to_pywr = {
    'water demand': 'base_flow',
    'runoff': 'flow',
    'violation cost': 'mrf_cost',
    'requirement': 'mrf',
    'value': 'cost',
    'cost': 'cost',
    'turbine capacity': 'turbine_capacity',
    'demand': 'max_flow',
    'base value': 'base_cost',
    'excess value': 'excess_cost',
    # 'Storage Demand': 'max_volume',
    'storage value': 'cost',
    'inactive pool': 'min_volume',
    'flow capacity': 'max_flow',
    'storage capacity': 'max_volume',
    'storage': 'storage',
    'outflow': 'flow',
    'flow': 'flow'
}

oa_type_to_pywr = {
    'Reservoir': 'Storage',
    'Groundwater': 'Storage',
    'Outflow Node': 'Output',
    'Urban Demand': 'Output',
    'General Demand': 'Output',
    'Agricultural Demand': 'Output',
    'Inflow Node': 'Catchment',
    'Misc Source': 'Catchment',
    'Catchment': 'Catchment',
    'Diversion Reservoir': 'Link',
    'Hydropower': 'Hydropower',
    'Flow Requirement': 'InstreamFlowRequirement',
    'River': 'River',
    'Conveyance': 'Link',
    'Streamflow Gauge': 'RiverGauge',
    'Junction': 'Link',
}

pywr_storage_types = ['Storage']
pywr_output_types = ['Output']
pywr_input_types = ['Input', 'Catchment']
pywr_node_types = ['Hydropower', 'InstreamFlowRequirement']
pywr_link_types = ['Link', 'River']

recorders = {
    'storage': 'NumpyArrayStorageRecorder',
    'flow': 'NumpyArrayNodeRecorder',
}


def negative(value):
    return -abs(value) if type(value) in [int, float] else value


def load_modules(folder):
    for filename in os.listdir(folder):
        if '__init__' in filename:
            continue
        policy_name = os.path.splitext(filename)[0]
        policy_module = '.{policy_name}'.format(policy_name=policy_name)
        package = '.{}'.format(folder)
        import_module(policy_module, package)


def load_from_s3(bucket, network_key, path, dest_root):
    s3 = boto3.client('s3')

    if path:
        prefix = '{}/{}'.format(network_key, path)
        response = s3.list_objects(
            Bucket=bucket,
            Prefix=prefix
        )

        for file in response.get('Contents', []):
            name = file['Key'].rsplit('/', 1)
            if name[1]:
                src = file['Key']
                dest = '{}/{}/{}'.format(dest_root, path, name[1])
                dest_folder = '/'.join(os.path.split(dest)[:-1])
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder)
                s3.download_file(bucket, src, dest)


# create the model
class PywrModel(object):
    def __init__(self, network, template, start=None, end=None, step=None, tattrs=None,
                 constants=None, variables=None, parameters=None, urls=None, modules=None, initial_volumes=None,
                 check_graph=False):

        self.model = None
        self.storage = {}
        self.non_storage = {}
        self.updated = {}  # dictionary for debugging whether or not a param has been updated

        self.here = os.path.dirname(os.path.abspath(__file__))
        tmp_dir = os.path.join(self.here, 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        self.root_dir = mkdtemp(dir=tmp_dir)
        os.chdir(self.root_dir)

        self.parameters_folder = os.path.join(self.root_dir, '_parameters')

        if not os.path.exists(self.parameters_folder):
            os.mkdir(self.parameters_folder)
            with open(os.path.join(self.parameters_folder, '__init__.py'), 'w') as f:
                f.write('\n')

        self.model_filename = os.path.join(self.root_dir, 'pywr_model.json')

        metadata = {
            'title': network['name'],
            'description': network['description'],
            'minimum_version': '1.0.0'
        }

        # Copy domains and parameters into temp folder
        for folder in os.listdir(os.path.join(self.here, 'base')):
            copytree(os.path.join(self.here, 'base', folder), os.path.join(self.root_dir, folder))

        self.create_model(
            network, template,
            filename=self.model_filename,
            start=start,
            end=end,
            step=step,
            constants=constants,
            parameters=parameters,
            initial_volumes=initial_volumes,
            metadata=metadata,
            tattrs=tattrs
        )

        # Copy policy folders from S3
        network_key = network.layout.get('storage', {}).get('folder')
        bucket = 'openagua-networks'
        policy_folders = ['policies']
        for folder in policy_folders:
            load_from_s3(bucket, network_key, folder, self.root_dir)
            # load_modules(folder)

        self.load_model(self.root_dir, self.model_filename, bucket=bucket, network_key=network_key)

    def load_model(self, root_dir, model_path, bucket=None, network_key=None, check_graph=False):

        os.chdir(root_dir)

        # needed when loading JSON file
        root_path = 's3://{}/{}/'.format(bucket, network_key)
        os.environ['ROOT_S3_PATH'] = root_path

        # Step 1: Load and register policies
        sys.path.insert(0, os.getcwd())
        policy_folder = '_parameters'
        for filename in os.listdir(policy_folder):
            if '__init__' in filename:
                continue
            policy_name = os.path.splitext(filename)[0]
            policy_module = '.{policy_name}'.format(policy_name=policy_name)
            # package = '.{}'.format(policy_folder)
            import_module(policy_module, policy_folder)

        # from domains import Hydropower, InstreamFlowRequirement

        modules = [
            ('.IFRS', 'policies'),
            ('.domains', 'domains')
        ]
        for name, package in modules:
            try:
                import_module(name, package)
            except:
                print(' [-] WARNING: {} could not be imported from {}'.format(name, package))

        # Step 2: Load and run model
        self.model = Model.load(model_path, path=model_path)

        # check network graph
        if check_graph:
            try:
                self.model.check_graph()
            except Exception as err:
                raise Exception('Pywr error: {}'.format(err))

        self.setup()

        return

    def create_model(self, network, template, start=None, end=None, step=None, initial_volumes=None, filename=None, human_readable=False,
                     metadata=None, tattrs=None, **kwargs):

        constants = kwargs.get('constants', {})
        parameters = kwargs.get('parameters', {})

        # Create folders
        if not os.path.exists('_parameters'):
            os.mkdir('_parameters')

        timestepper = {
            'start': pandas.Timestamp(start).strftime('%Y-%m-%d'),
            'end': pandas.Timestamp(end).strftime('%Y-%m-%d'),
            'timestep': step
        }

        output_ids = []
        input_ids = []

        # convert nodes
        pywr_nodes = []
        pywr_edges = []
        pywr_params = {}
        pywr_recorders = {}

        node_lookup = {}

        storage = {}
        non_storage = {}

        non_storage_types = pywr_output_types + pywr_input_types + pywr_node_types

        res_attr_lookup = {'%s/%s/%s' % idx: parameters[idx]['value']['name'] for idx in parameters}

        def make_pywr_param(res_attr_idx, tattr):
            pywr_param = None

            # constants
            constant = constants.pop(res_attr_idx, None)
            if constant:
                return constant

            parameter = parameters.pop(res_attr_idx, None)

            if parameter is None:
                return

            ptype = parameter['type']
            pvalue = parameter['value']
            param_name = pvalue.get('name')
            pywr_param = None
            if ptype == 'variable':
                pywr_param = create_variable(pvalue)
            elif ptype == 'parameter':
                pywr_param = create_policy(pvalue, self.parameters_folder, res_attr_lookup, tattr)
            elif ptype == 'controlcurve':

                pywr_param = create_control_curve(node_lookup=node_lookup, **pvalue)
            elif ptype == 'module':
                # pywr_param = create_module(module)
                module = pvalue
                param_name = module.get('path')
                if not param_name:
                    return None
                pywr_param = {'type': param_name}

            elif ptype == 'descriptor':
                pywr_param = {
                    'type': 'constant',
                    'value': pvalue['value']
                }

            # update the Pywr parameters object
            if pywr_param:
                pywr_params[param_name] = pywr_param

                return param_name

            else:
                return pywr_param

        def process_param(pywr_node, resource_type, resource, ra):
            try:
                res_attr_idx = (resource_type, resource['id'], ra['attr_id'])
                attr_name = ra['attr_name']
                tattr = tattrs.get(res_attr_idx)
                if not tattr:
                    return pywr_node

                properties = tattr['properties']

                pywr_attr_name = oa_attr_to_pywr.get(attr_name.lower())

                try:
                    pywr_param = make_pywr_param(res_attr_idx, tattr)
                except Exception as err:
                    print(err)
                    print('Failed to prepare {}'.format(attr_name.lower()))
                    raise
                if pywr_node and pywr_attr_name and pywr_param and not properties.get('intermediary'):
                    pywr_node.update({
                        pywr_attr_name: pywr_param
                    })

                # create recorder for attribute
                if properties.get('save'):
                    resource_class = res_attr_idx[0]
                    recorder_name = '{}/{}/{}'.format(
                        resource_class,
                        resource['name'],
                        attr_name.lower()
                    )

                    recorder = None
                    recorder_type = recorders.get(pywr_attr_name, 'NumpyArrayParameterRecorder')
                    if recorder_type == 'NumpyArrayParameterRecorder':
                        if pywr_param and type(pywr_param) == str:
                            recorder = {
                                'type': recorder_type,
                                'parameter': pywr_param
                            }
                    else:
                        recorder = {
                            'type': recorder_type,
                            'node': pywr_name,
                        }

                    if recorder:
                        pywr_recorders[recorder_name] = recorder

                return pywr_node
            except:
                raise

        # create node dictionaries by name and id
        for node in network['nodes']:
            pywr_name = resource_name(node['name'], 'node')
            types = [t for t in node['types'] if t['template_id'] == template['id']]
            if not types:
                continue
            elif len(types) > 1:
                msg = "Type is ambiguous for {}. Please remove extra types.".format(pywr_name)
                raise Exception(msg)

            type_name = types[-1]['name']
            pywr_type = oa_type_to_pywr.get(type_name)
            if not pywr_type:
                msg = "No default type found for {}. Please map a Pywr type to this template type".format(type_name)
                raise Exception(msg)

            node_lookup[node["id"]] = {
                'id': node['id'],
                'name': node['name'],
                'pywr_name': pywr_name,
                'pywr_type': pywr_type,
                'connect_in': 0,
                'connect_out': 0,
                'attributes': node['attributes']
            }
            if pywr_type in pywr_output_types:
                output_ids.append(node['id'])
            elif pywr_type in pywr_input_types:
                input_ids.append(node['id'])

        # create link lookups and pywr links
        link_lookup = {}
        for link in network['links']:
            try:
                pywr_name = resource_name(link['name'], 'link')
                types = [t for t in link['types'] if t['template_id'] == template['id']]
                if not types:
                    continue
                type_name = types[-1]['name']
                link_id = link['id']
                node_1_id = link['node_1_id']
                node_2_id = link['node_2_id']
                node_1 = node_lookup[node_1_id]
                node_2 = node_lookup[node_2_id]
                node_1['connect_out'] += 1
                node_2['connect_in'] += 1
                link_lookup[link_id] = {
                    'pywr_name': pywr_name,
                    'node_1_id': node_1_id,
                    'node_2_id': node_2_id,
                    'from_slot': node_1['connect_out'],
                    'to_slot': node_2['connect_in'],
                }

                if node_1_id in output_ids:
                    msg = 'Topology error: Output "{}" appears to be upstream of "{}"'\
                        .format(node_1['pywr_name'], pywr_name)
                    raise Exception(msg)
                elif node_2_id in input_ids:
                    msg = 'Topology error: Input "{}" appears to be downstream of "{}"'\
                        .format(node_2['pywr_name'], pywr_name)
                    raise Exception(msg)

                pywr_type = oa_type_to_pywr.get(type_name, 'Link')

                pywr_node = {
                    'name': pywr_name,
                    'type': pywr_type
                }
                non_storage[('link', link_id)] = pywr_node

                # Add data
                for ra in link['attributes']:
                    pywr_node = process_param(pywr_node, 'link', link, ra)

                pywr_nodes.append(pywr_node)
            except:
                raise

        # Q/C

        # remove unconnected links
        d = []
        for link_id, link in link_lookup.items():
            if link['node_1_id'] not in node_lookup or link['node_2_id'] not in node_lookup:
                d.append(link_id)
        for link_id in d:
            del link_lookup[link_id]

        connected_nodes = []
        for link_id, link in link_lookup.items():
            connected_nodes.append(link['node_1_id'])
            connected_nodes.append(link['node_2_id'])

        # remove unconnected nodes
        d = []
        for node_id in node_lookup:
            if node_id not in connected_nodes:
                d.append(node_id)
        for node_id in d:
            del node_lookup[node_id]

        # create pywr nodes dictionary with format ["name" = pywr type + 'name']
        # for storage and non storage

        for node_id, node in node_lookup.items():

            pywr_name = node['pywr_name']
            pywr_type = node['pywr_type']
            connect_in = node.get('connect_in', 0)
            connect_out = node.get('connect_out', 0)

            pywr_node = {
                'name': pywr_name,
                'type': pywr_type,
            }

            if (pywr_type in pywr_storage_types or connect_out > 1) and pywr_type not in non_storage_types:
                pywr_node.update({
                    'type': 'Storage',
                    'initial_volume': initial_volumes.get(node_id, 0.0) if initial_volumes is not None else 0.0,
                    # 'num_outputs': connect_in,
                    # 'num_inputs': connect_out,
                    'max_volume': 0.0
                })
                # if pywr_type not in pywr_storage_types:
                #     pywr_node['max_volume'] = 0.0
                storage[node_id] = pywr_node

            else:
                if connect_in > 1:
                    pywr_node['type'] = 'River'
                non_storage[('node', node_id)] = pywr_node

            for ra in node['attributes']:
                pywr_node = process_param(pywr_node, 'node', node, ra)

            if pywr_node['type'] == 'Storage':
                pywr_node['max_volume'] = pywr_node.get('max_volume', 0.0)
            if pywr_node['type'] == 'RiverGauge':
                pywr_node['mrf'] = pywr_node.get('mrf', 0.0)
                pywr_node['mrf_cost'] = pywr_node.get('mrf_cost', 0.0)

            pywr_nodes.append(pywr_node)

        for link_id, link in link_lookup.items():
            node_1 = node_lookup[link['node_1_id']]
            node_2 = node_lookup[link['node_2_id']]

            up_edge = [node_1['pywr_name'], link['pywr_name']]
            down_edge = [link['pywr_name'], node_2['pywr_name']]

            # up_storage = storage.get(node_1['id'])
            # down_storage = storage.get(node_2['id'])

            # if up_storage:
            #     up_edge.append(link['from_slot'])
            # if down_storage:
            #     down_edge.append(link['to_slot'])
            pywr_edges.extend([up_edge, down_edge])

        # Finally, map network attributes to parameters
        for ra in network['attributes']:
            process_param({}, 'network', network, ra)

        pywr_model = {
            'metadata': metadata,
            'timestepper': timestepper,
            'solver': {'name': 'glpk'},
            'nodes': pywr_nodes,
            'edges': pywr_edges,
            'parameters': pywr_params,
            'recorders': pywr_recorders
        }

        with open(filename, 'w') as f:
            json.dump(pywr_model, f, indent=4)

    def setup(self):
        try:
            self.model.setup()
            return
        except Exception as err:
            print(err)
            raise

    def step(self):
        self.model.step()

    def finish(self):
        self.model.finish()
        self.cleanup()

    def cleanup(self):
        if os.path.exists(self.root_dir):
            rmtree(self.root_dir)
