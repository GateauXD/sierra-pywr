import re


def clean_parameter_name(s):
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '_', s)

    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '_', s)

    return s


spaces = '\n' + ' ' * 8

default_value_code = 'self._value(timestep, scenario_index)'
value_code_template = 'convert({value}, "{unit1}", "{unit2}", scale_in={scale_in}, scale_out={scale_out})'

policy_code_template = """from parameters import WaterLPParameter

from utilities.converter import convert

class {policy_name}(WaterLPParameter):
    \"\"\"{policy_description}\"\"\"

    def _value(self, timestep, scenario_index):
        {kwargs}
        {policy_code}
        
    def value(self, timestep, scenario_index):
        return {value_code}

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
{policy_name}.register()
print(" [*] {policy_name} successfully registered")
"""


def parse_code(policy_name, user_code, res_attr_lookup, tattr, description=''):
    """
    Parse a code snippet into a Pywr policy
    :param policy_name: The name of the policy
    :param user_code: Code from the user via OpenAgua
    :param description: Description of the policy
    :return:
    """

    pattern1 = r'"([A-Za-z0-9_\./\\-]*)"'
    pattern2 = r"'([A-Za-z0-9_\./\\-]*)'"

    # first, parse code
    s = user_code.rstrip()
    lines = s.split('\n')
    stripped = ''
    for line in reversed(lines):
        stripped = line.strip()
        if stripped and stripped[0] == '#':
            stripped = ''
            continue
        if stripped and stripped[0] != '#':
            break
    if len(stripped) <= 7 or stripped[:7] != 'return ':
        if not stripped:
            lines.append('return 0')
        else:
            lines[-1] = 'return ' + lines[-1]

    for i in range(len(lines)):
        line = lines[i]
        for pattern in [pattern1, pattern2]:
            m = re.search(pattern, line)
            if m:
                for g in m.groups():
                    r = res_attr_lookup.get(g)
                    if r:
                        lines[i] = line.replace(g, r)

    new_code = spaces.join(lines)

    # value code
    dim = tattr.get('dimension')
    unit1 = tattr.get('unit')
    scale_in = tattr.get('properties').get('scale', 1)
    unit2 = None
    if dim == 'Volume':
        unit2 = 'm^3'
    elif dim == 'Volumetric flow rate':
        unit2 = 'm^3 day^-1'
    scale_out = 1e6

    if unit2 and (unit1 != unit2 or scale_in != scale_out):
        value_code = value_code_template.format(
            value=default_value_code,
            unit1=unit1,
            unit2=unit2,
            scale_in=scale_in,
            scale_out=scale_out
        )
    else:
        value_code = default_value_code

    policy_str = policy_code_template.format(
        policy_name=policy_name,
        policy_description=description,
        policy_code=new_code,
        value_code = value_code,
        kwargs='kwargs = dict(timestep=timestep, scenario_index=scenario_index)' if '**kwargs' in user_code else ''
    )

    return policy_str


def create_variable(variable):
    pywr_type = variable.get('pywr_type', 'ArrayIndexed')

    parameter = {
        'type': pywr_type,
    }

    if pywr_type == 'constant':
        parameter['value'] = variable['value']
    else:
        parameter['values'] = list(variable['value'][0].values())

    return parameter


def create_control_curve(name=None, data=None, node_lookup=None):
    curve_type = data.get('type')
    storage_node = data.get('storage_node')
    node = node_lookup.get(int(storage_node))
    storage_node_name = resource_name(node['name'], 'node')
    _values = data.get('values')

    control_curve = {}

    if curve_type == 'simple':
        c = _values[0]
        values = []
        try:
            reference_level = float(c)
        except:
            reference_level = c
        for v in _values[1:]:
            try:
                values.append(float(v))
            except:
                values.append(v)
        control_curve = {
            'type': 'controlcurve',
            'storage_node': storage_node_name,
            'control_curve': reference_level,
            'values': values
        }

    elif curve_type == 'interpolated':
        reference_levels = []
        values = []

        for i, (c, v) in enumerate(_values):

            if 0 < i < len(_values) - 1:
                try:
                    reference_levels.append(float(c))
                except:
                    reference_levels.append(c)

            try:
                values.append(float(v))
            except:
                values.append(v)

        control_curve = {
            'type': 'controlcurveinterpolated',
            'storage_node': storage_node_name,
            'control_curves': reference_levels,
            'values': values
        }

    return control_curve


def create_policy(policy, policies_folder, res_attr_lookup, tattr):
    policy_name = clean_parameter_name(policy['name'])
    policy_code = parse_code(policy_name, policy['code'], res_attr_lookup, tattr, policy.get('description', ''))
    policy_path = '{}/{}.py'.format(policies_folder, policy_name)

    with open(policy_path, 'w') as f:
        f.writelines(policy_code)

    ret = {'type': policy_name}

    return ret


def resource_name(rname, rtype):
    return '{} [{}]'.format(rname, rtype)
