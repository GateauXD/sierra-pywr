import os
import datetime
import json
import pandas

from pywr.core import Model, Input, Output, Link, Timestepper
from pywr.domains.river import River, Storage, RiverGauge, Catchment
from pywr.parameters import ArrayIndexedParameter, DataFrameParameter, ConstantParameter

from .domains import Hydropower, InstreamFlowRequirement

from .utils import clean, parse_code, resource_name

# from pywr.recorders import (NumpyArrayNodeRecorder, NumpyArrayStorageRecorder)

storage_types = {
    'Reservoir': Storage,
    'Groundwater': Storage,
}
output_types = {
    'Outflow Node': Output,
    'Urban Demand': Output,
    'General Demand': Output,
    'Agricultural Demand': Output,
}
input_types = {
    'Inflow Node': Catchment,
    'Misc Source': Input,
    'Catchment': Catchment,
}
node_types = {
    'Hydropower': Hydropower,
    'Flow Requirement': InstreamFlowRequirement,
}

link_types = {
    'River': River,
}

oa_attr_to_pywr = {
    'Water Demand': 'max_flow',
    'Runoff': 'flow',
    'Violation Cost': 'mrf_cost',
    'Requirement': 'mrf',
    'Value': 'cost',
    'Turbine Capacity': 'turbine_capacity',
    'Demand': 'max_flow',
    'Base Cost': 'base_cost',
    'Excess Cost': 'excess_cost',
    'Storage Demand': 'max_volume',
    'Storage Value': 'cost',
    'Inactive Pool': 'min_volume',
    'Flow Capacity': 'max_flow',
    # 'Storage Capacity': 'max_volume'
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
    'Conveyance': 'Link'
}


def negative(value):
    return -abs(value) if type(value) in [int, float] else value


# create the model
class PywrModel(object):
    def __init__(self, network, template, start=None, end=None, step=None,
                 constants=None, variables=None, policies=None, initial_volumes=None,
                 check_graph=False):

        self.model = None
        self.storage = {}
        self.non_storage = {}
        self.updated = {}  # dictionary for debugging whether or not a param has been updated

        self.here = os.path.dirname(os.path.abspath(__file__))
        self.policies_folder = '{}/policies'.format(self.here)

        if not os.path.exists(self.policies_folder):
            os.mkdir(self.policies_folder)
            with open('{}/__init__.py'.format(self.policies_folder), 'w') as f:
                f.write('\n')

        # self.create_model(network, template, constants=constants, variables=variables, policies=policies,
        #                   initial_volumes=initial_volumes)

        self.create_model2(network, template, start=start, end=end, step=step, constants=constants, variables=variables,
                           policies=policies,
                           initial_volumes=initial_volumes)

        # check network graph
        if check_graph:
            try:
                self.model.check_graph()
            except Exception as err:
                raise Exception('Pywr error: {}'.format(err))

        self.setup(start=start, end=end, step=step)

    def create_model(self, network, template, constants=None, variables=None, policies=None, initial_volumes=None):

        model = Model(solver='glpk-edge')

        # -----------------GENERATE NETWORK STRUCTURE -----------------------
        # ...and add initial parameter values

        output_ids = []
        input_ids = []

        non_storage_types = list(output_types.keys()) + list(input_types.keys()) + list(node_types.keys())

        def add_value_to_node(res_attr_idx, type_name, attr_name):
            pywr_param = None
            constant = constants.pop(res_attr_idx, None)
            if constant:
                pywr_param = ConstantParameter(model, constant)
            elif variables:
                variable = variables.pop(res_attr_idx, None)
                if variable:
                    values = list(variable['values'].values())
                    pywr_param = ArrayIndexedParameter(model, values)
            elif policies:
                policy = policies.pop(res_attr_idx, None)
                if policy:
                    pywr_param = self.create_register_policy(policy)

            if pywr_param is not None:
                type_name = type_name.lower()
                attr_name = attr_name.lower()
                (resource_type, resource_id, attr_id) = res_attr_idx
                try:
                    self.update_param(resource_type, resource_id, type_name, attr_name, value=pywr_param)
                except:
                    raise

        # create node dictionaries by name and id
        node_lookup = {}
        for node in network['nodes']:
            name = '{} (node)'.format(node['name'])
            types = [t for t in node['types'] if t['template_id'] == template['id']]
            if not types:
                continue
            if len(types) > 1:
                msg = "Type is ambiguous for {}. Please remove extra types.".format(name)
                raise Exception(msg)
            type_name = types[-1]['name']
            node_lookup[node.get("id")] = {
                'type': type_name,
                'name': name,
                'connect_in': 0,
                'connect_out': 0,
                'attributes': node['attributes']
            }
            if type_name in output_types:
                output_ids.append(node['id'])
            elif type_name in input_types:
                input_ids.append(node['id'])

        # create link lookups and pywr links
        link_lookup = {}
        for link in network['links']:
            residx = ('link', link['id'])
            name = '{} (link)'.format(link['name'])
            types = [t for t in link['types'] if t['template_id'] == template['id']]
            if not types:
                continue
            type_name = types[-1]['name']
            link_id = link['id']
            node_1_id = link['node_1_id']
            node_2_id = link['node_2_id']
            node_lookup[node_1_id]['connect_out'] += 1
            node_lookup[node_2_id]['connect_in'] += 1
            link_lookup[link_id] = {
                'name': name,
                'type': type_name,
                'node_1_id': node_1_id,
                'node_2_id': node_2_id,
                'from_slot': node_lookup[node_1_id]['connect_out'] - 1,
                'to_slot': node_lookup[node_2_id]['connect_in'] - 1,
            }

            if node_1_id in output_ids:
                node = node_lookup[node_1_id]
                msg = 'Topology error: Output {} appears to be upstream of {}'.format(node['name'], name)
                raise Exception(msg)
            elif node_2_id in input_ids:
                node = node_lookup[node_2_id]
                msg = 'Topology error: Input {} appears to be downstream of {}'.format(node['name'], name)
                raise Exception(msg)

            LinkType = link_types.get(type_name, Link)

            self.non_storage[residx] = LinkType(model, name=name)

            for ra in link['attributes']:
                res_attr_idx = ('link', link['id'], ra['attr_id'])
                add_value_to_node(res_attr_idx, type_name, ra['attr_name'])

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
            residx = ('node', node_id)
            type_name = node['type']
            name = node['name']
            connect_in = node.get('connect_in', 0)
            connect_out = node.get('connect_out', 0)
            if (type_name in storage_types or connect_out > 1) and type_name not in non_storage_types:
                self.storage[node_id] = Storage(
                    model,
                    name=name,
                    num_outputs=connect_in,
                    num_inputs=connect_out,
                    initial_volume=initial_volumes.get(node_id, 0.0) if initial_volumes is not None else 0.0
                )
                if type_name not in storage_types:
                    self.storage[node_id].max_volume = 0.0
            else:

                if type_name in input_types:
                    NodeType = input_types[type_name]
                elif type_name in output_types:
                    NodeType = output_types[type_name]
                elif type_name in node_types:
                    NodeType = node_types[type_name]
                elif connect_in > 1:
                    NodeType = River
                else:
                    NodeType = Link

                self.non_storage[residx] = NodeType(model, name=name)

            for ra in node['attributes']:
                res_attr_idx = ('node', node_id, ra['attr_id'])
                try:
                    add_value_to_node(res_attr_idx, type_name, ra['attr_name'])
                except Exception as err:
                    print(err)
                    raise

        # create network connections
        # must assign connection slots for storage
        # TODO: change looping variable notation
        for link_id, link in link_lookup.items():
            node_1_id = link['node_1_id']
            node_2_id = link['node_2_id']

            _link = self.non_storage[('link', link_id)]
            up_storage = self.storage.get(node_1_id)
            up_node = self.non_storage.get(('node', node_1_id))
            down_storage = self.storage.get(node_2_id)
            down_node = self.non_storage.get(('node', node_2_id))

            if up_storage:
                up_storage.connect(_link, from_slot=link['from_slot'])
            else:
                up_node.connect(_link)

            if down_storage:
                _link.connect(down_storage, to_slot=link['to_slot'])
            else:
                _link.connect(down_node)

        self.model = model

    def create_model2(self, network, template, start=None, end=None, step=None, constants=None, variables=None,
                      policies=None, initial_volumes=None):

        # Create folders
        if not os.path.exists('policies'):
            os.mkdir('policies')
        policy_names = []

        timesteps = dict(day=1)
        timestepper = {
            'start': start,
            'end': start,
            'timestep': start
        }

        output_ids = []
        input_ids = []

        node_lookup = {n['id']: n for n in network['nodes']}
        type_lookup = {tt['id']: tt for tt in template['types']}

        # convert nodes
        pywr_nodes = []
        pywr_edges = []
        non_storage = {}

        non_storage_types = list(output_types.keys()) + list(input_types.keys()) + list(node_types.keys())

        def get_pywr_value(res_attr_idx):
            pywr_param = None
            constant = constants.pop(res_attr_idx, None)
            if constant:
                pywr_param = constant
            elif variables:
                variable = variables.pop(res_attr_idx, None)
                if variable:
                    values = list(variable['values'].values())
                    pywr_param = values
            elif policies:
                policy = policies.pop(res_attr_idx, None)
                if policy:
                    pywr_param = self.create_register_policy(policy)

            return pywr_param

        # create node dictionaries by name and id
        node_lookup = {}
        for node in network['nodes']:
            pywr_name = resource_name(node, 'node')
            types = [t for t in node['types'] if t['template_id'] == template['id']]
            if not types:
                continue
            type_name = types[-1]['name']
            if len(types) > 1:
                msg = "Type is ambiguous for {}. Please remove extra types.".format(name)
                raise Exception(msg)
            node_lookup[node.get("id")] = {
                'pywr_name': pywr_name,
                'type': type_name,
                'connect_in': 0,
                'connect_out': 0,
                'attributes': node['attributes']
            }
            if type_name in output_types:
                output_ids.append(node['id'])
            elif type_name in input_types:
                input_ids.append(node['id'])

        # create link lookups and pywr links
        link_lookup = {}
        for link in network['links']:
            residx = ('link', link['id'])
            pywr_name = resource_name(link, 'link')
            types = [t for t in link['types'] if t['template_id'] == template['id']]
            if not types:
                continue
            type_name = types[-1]['name']
            link_id = link['id']
            node_1_id = link['node_1_id']
            node_2_id = link['node_2_id']
            node_lookup[node_1_id]['connect_out'] += 1
            node_lookup[node_2_id]['connect_in'] += 1
            link_lookup[link_id] = {
                'pywr_name': pywr_name,
                'type': type_name,
                'node_1_id': node_1_id,
                'node_2_id': node_2_id,
                'from_slot': node_lookup[node_1_id]['connect_out'] - 1,
                'to_slot': node_lookup[node_2_id]['connect_in'] - 1,
                'attributes': link['attributes']
            }

            if node_1_id in output_ids:
                node = node_lookup[node_1_id]
                msg = 'Topology error: Output {} appears to be upstream of {}'.format(node['name'], pywr_name)
                raise Exception(msg)
            elif node_2_id in input_ids:
                node = node_lookup[node_2_id]
                msg = 'Topology error: Input {} appears to be downstream of {}'.format(node['name'], pywr_name)
                raise Exception(msg)

            pywr_type = oa_type_to_pywr.get(type_name)

            pywr_node = {
                'name': pywr_name,
                'type': pywr_type
            }

            for ra in link['attributes']:
                res_attr_idx = ('link', link_id, ra['attr_id'])
                pywr_value = get_pywr_value(res_attr_idx)
                if pywr_value:
                    pywr_node.update({
                        oa_attr_to_pywr[ra['attr_name']]: pywr_value
                    })

            pywr_nodes.append(pywr_node)

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
            type_name = node['type']
            connect_in = node.get('connect_in', 0)
            connect_out = node.get('connect_out', 0)

            pywr_type = oa_type_to_pywr.get(type_name, 'link')

            pywr_node = {
                'name': pywr_name,
                'type': pywr_type,
            }

            if (type_name in storage_types or connect_out > 1) and type_name not in non_storage_types:
                pywr_node.update({
                    'type': 'storage',
                    'num_outputs': connect_in,
                    'num_inputs': connect_out,
                    'initial_volume': initial_volumes.get(node_id, 0.0) if initial_volumes is not None else 0.0,
                })
                if type_name not in storage_types:
                    pywr_node['max_volume'] = 0.0
            else:
                if connect_in > 1:
                    pywr_node['type'] = 'river'

                pywr_node = {
                    'name': pywr_name,
                }

            for ra in node['attributes']:
                res_attr_idx = ('node', node_id, ra['attr_id'])
                pywr_attr_name = oa_attr_to_pywr.get(ra['attr_name'])
                if pywr_attr_name is None:
                    continue
                pywr_value = get_pywr_value(res_attr_idx)
                if pywr_attr_name and pywr_value:
                    pywr_node.update({
                        pywr_attr_name: pywr_value
                    })

            pywr_nodes.append(pywr_node)

        for link_id, link in link_lookup.items():
            node_1 = node_lookup[link['node_1_id']]
            node_2 = node_lookup[link['node_2_id']]

            pywr_edges.append([node_1['pywr_name'], link['pywr_name']])
            pywr_edges.append([link['pywr_name'], node_2['pywr_name']])

        pywr_model = {
            'metadata': {
                'title': network['name'],
                'description': network['description'],
            },
            'nodes': pywr_nodes,
            'edges': pywr_edges,
        }

        with open('pywr_model.json', 'w') as f:
            json.dump(pywr_model, f, indent=4)

    def setup(self, start, end, step):

        self.update_timesteps(
            start=start,
            end=end,
            step=step
        )

        try:
            self.model.setup()
            return
        except Exception as err:
            print(err)
            raise

    def update_timesteps(self, start, end, step):
        self.model.timestepper = Timestepper(
            pandas.to_datetime(start),  # start
            pandas.to_datetime(end),  # end
            datetime.timedelta(step)  # step
        )

    def update_param(self, resource_type, resource_id, type_name, attr_name, value):

        res_idx = (resource_type, resource_id)
        # attr_idx = (resource_type, resource_id, attr_name)

        ta = (type_name.lower(), attr_name.lower())

        try:

            if ta == ('catchment', 'runoff'):
                self.non_storage[res_idx].flow = value
            # elif ta == ('reservoir', 'initial storage'):
            #     self.storage[resource_id].initial_volume = value
            elif 'demand' in type_name:
                if attr_name == 'value':
                    self.non_storage[res_idx].cost = negative(value)
                elif attr_name == 'demand':
                    self.non_storage[res_idx].max_flow = value
            elif type_name == 'flow requirement':
                if attr_name == 'requirement':
                    self.non_storage[res_idx].mrf = value
                elif attr_name == 'violation cost':
                    self.non_storage[res_idx].mrf_cost = negative(value)
            if type_name == 'hydropower':
                if attr_name == 'water demand':
                    self.non_storage[res_idx].base_flow = value
                elif attr_name == 'base value':
                    self.non_storage[res_idx].base_cost = negative(value)
                elif attr_name == 'turbine capacity':
                    self.non_storage[res_idx].turbine_capacity = value
                elif attr_name == 'excess value':
                    self.non_storage[res_idx].excess_cost = negative(value)
            elif attr_name == 'storage demand':
                self.storage[resource_id].max_volume = value
            elif attr_name == 'storage value':
                self.storage[resource_id].cost = value
            elif attr_name == 'storage capacity':
                self.storage[resource_id].max_volume = value
            elif attr_name == 'inactive pool':
                self.storage[resource_id].min_volume = value
            elif attr_name == 'flow capacity':
                self.non_storage[res_idx].max_flow = value

        except Exception as err:
            msg = 'Failed to prepare Pywr data for {} {}'.format(type_name, attr_name)
            raise Exception(msg)

        return

    def create_register_policy(self, policy):

        policy_name = clean(policy['name'])
        policy_code = parse_code(policy_name, policy['code'], policy.get('description', ''))
        policy_path = '{}/{}.py'.format(self.policies_folder, policy_name)

        with open(policy_path, 'w') as f:
            f.writelines(policy_code)

        exec('from .policies.{p} import {p}'.format(p=policy_name))
        policy = eval(policy_name)
        policy.register()

        return policy_name
