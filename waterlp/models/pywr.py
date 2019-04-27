import os
import datetime
import json
import pandas

from pywr.core import Model

# needed when loading JSON file
from .domains import Hydropower, InstreamFlowRequirement

from .utils import resource_name, create_register_policy

oa_attr_to_pywr = {
    'Water Demand': 'base_flow',
    'Runoff': 'flow',
    'Violation Cost': 'mrf_cost',
    'Requirement': 'mrf',
    'Value': 'cost',
    'Turbine Capacity': 'turbine_capacity',
    'Demand': 'max_flow',
    'Base Value': 'base_cost',
    'Excess Value': 'excess_cost',
    'Storage Demand': 'max_volume',
    'Storage Value': 'cost',
    'Inactive Pool': 'min_volume',
    'Flow Capacity': 'max_flow',
    # 'Storage Capacity': 'max_volume'
    'Storage': 'storage',
    'Outflow': 'flow',
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


# create the model
class PywrModel(object):
    def __init__(self, network, template, start=None, end=None, step=None, tattrs=None,
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

        self.model_filename = 'pywr_model.json'

        metadata = {
            'title': network['name'],
            'description': network['description'],
            'minimum_version': '1.0.0'
        }

        self.create_model(
            network, template, filename=self.model_filename, start=start, end=end, step=step,
            constants=constants, variables=variables,
            policies=policies, initial_volumes=initial_volumes,
            metadata=metadata, tattrs=tattrs
        )

        self.model = Model.load(self.model_filename)

        # check network graph
        if check_graph:
            try:
                self.model.check_graph()
            except Exception as err:
                raise Exception('Pywr error: {}'.format(err))

        self.setup()

    def create_model(self, network, template, start=None, end=None, step=None, constants=None, variables=None,
                     policies=None, initial_volumes=None, filename=None, metadata=None, tattrs=None):

        # Create folders
        if not os.path.exists('policies'):
            os.mkdir('policies')

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

        non_storage_types = pywr_output_types + pywr_input_types + pywr_node_types

        def make_pywr_param(res_attr_idx):
            pywr_param = None

            # constants
            constant = constants.pop(res_attr_idx, None)
            if constant:
                return constant

            # variables
            elif variables:
                variable = variables.pop(res_attr_idx, None)
                if variable:
                    values = list(variable['values'].values())
                    pywr_param = {
                        'name': variable['name'],
                        'value': values
                    }

            # policies
            elif policies:
                policy = policies.pop(res_attr_idx, None)
                if policy:
                    pywr_param = create_register_policy(policy, self.policies_folder)

            if pywr_param:
                pywr_params.update(pywr_param['value'])

                return pywr_param['name']

            else:
                return pywr_param

        def process_param(pywr_node, res_attr_idx):
            tattr = tattrs.get(res_attr_idx)
            if not tattr:
                return pywr_node

            pywr_attr_name = oa_attr_to_pywr.get(ra['attr_name'])
            if pywr_attr_name is None:
                return pywr_node

            if tattr and tattr['properties'].get('save'):
                recorder_name = recorders.get(pywr_attr_name)
                if recorder_name:
                    pywr_recorders['%s/%s/%s' % res_attr_idx] = {
                        'type': recorder_name,
                        'node': pywr_name,
                    }
            if tattr['is_var'] == 'Y':
                return pywr_node

            pywr_param = make_pywr_param(res_attr_idx)
            if pywr_attr_name and pywr_param:
                pywr_node.update({
                    pywr_attr_name: pywr_param
                })

            return pywr_node

        # create node dictionaries by name and id
        node_lookup = {}
        for node in network['nodes']:
            pywr_name = resource_name(node, 'node')
            types = [t for t in node['types'] if t['template_id'] == template['id']]
            if not types:
                continue
            type_name = types[-1]['name']
            pywr_type = oa_type_to_pywr.get(type_name)
            if len(types) > 1:
                msg = "Type is ambiguous for {}. Please remove extra types.".format(type_name)
                raise Exception(msg)
            node_lookup[node.get("id")] = {
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
            pywr_name = resource_name(link, 'Link')
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
                'node_1_id': node_1_id,
                'node_2_id': node_2_id,
            }

            if node_1_id in output_ids:
                node = node_lookup[node_1_id]
                msg = 'Topology error: Output {} appears to be upstream of {}'.format(node['name'], pywr_name)
                raise Exception(msg)
            elif node_2_id in input_ids:
                node = node_lookup[node_2_id]
                msg = 'Topology error: Input {} appears to be downstream of {}'.format(node['name'], pywr_name)
                raise Exception(msg)

            pywr_type = oa_type_to_pywr.get(type_name, 'Link')

            pywr_node = {
                'name': pywr_name,
                'type': pywr_type
            }

            # Add data
            for ra in link['attributes']:
                res_attr_idx = ('link', link_id, ra['attr_id'])
                pywr_node = process_param(pywr_node, res_attr_idx)

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
                })
                if pywr_type not in pywr_storage_types:
                    pywr_node['max_volume'] = 0.0

            else:
                if connect_in > 1:
                    pywr_node['type'] = 'River'

            for ra in node['attributes']:
                res_attr_idx = ('node', node_id, ra['attr_id'])
                pywr_node = process_param(pywr_node, res_attr_idx)

            pywr_nodes.append(pywr_node)

        for link_id, link in link_lookup.items():
            node_1 = node_lookup[link['node_1_id']]
            node_2 = node_lookup[link['node_2_id']]

            pywr_edges.append([node_1['pywr_name'], link['pywr_name']])
            pywr_edges.append([link['pywr_name'], node_2['pywr_name']])

        pywr_model = {
            'metadata': metadata,
            'timestepper': timestepper,
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
