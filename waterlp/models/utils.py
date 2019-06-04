import re


def clean(s):
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '_', s)

    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '_', s)

    return s


spaces = '\n' + ' ' * 8

policy_code_template = """from parameters import WaterLPParameter


class {policy_name}(WaterLPParameter):
    \"\"\"{policy_description}\"\"\"

    def value(self, timestep, scenario_index):

        {policy_code} 

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
{policy_name}.register()
print(" [*] {policy_name} successfully registered")
"""


def parse_code(policy_name, user_code, description=''):
    """
    Parse a code snippet into a Pywr policy
    :param policy_name: The name of the policy
    :param user_code: Code from the user via OpenAgua
    :param description: Description of the policy
    :return:
    """

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

    new_code = spaces.join(lines)

    policy_str = policy_code_template.format(
        policy_name=policy_name,
        policy_description=description,
        policy_code=new_code
    )

    return policy_str


def create_variable(variable):
    variable_name = clean(variable['name'])

    pywr_type = variable.get('pywr_type', 'ArrayIndexed')

    parameter = {
        'type': pywr_type,
    }

    if pywr_type == 'constant':
        parameter['value'] = variable['value']
    else:
        parameter['values'] = list(variable['value'][0].values())

    return {
        'name': variable_name,
        'value': {
            variable_name: parameter
        }
    }


def create_control_curve(name=None, data=None, node_lookup=None):
    curve_type = data.get('type')
    storage_node = data.get('storage_node')
    node = node_lookup.get(int(storage_node))
    storage_node_name = resource_name(node['name'], 'node')
    _values = data.get('values')

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

    control_curve_name = clean(name)

    ret = {
        'name': control_curve_name,
        'value': {
            control_curve_name: control_curve
        },
    }

    return ret


def create_policy(policy, policies_folder):
    policy_name = clean(policy['name'])
    policy_code = parse_code(policy_name, policy['code'], policy.get('description', ''))
    policy_path = '{}/{}.py'.format(policies_folder, policy_name)

    with open(policy_path, 'w') as f:
        f.writelines(policy_code)

    ret = {
        'name': policy_name,
        'value': {
            policy_name: {
                'type': policy_name
            }
        }
    }

    return ret


def resource_name(rname, rtype):
    return '{} [{}]'.format(rname, rtype)
