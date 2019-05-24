import os
import re


def clean(s):
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '_', s)

    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '_', s)

    return s


spaces = '\n' + ' ' * 8

init_code_template = """from waterlp.model.parameters import WaterLPParameter

WaterLPParameter.root_path = "{root_path}"

"""


def parse_init(root_path=''):
    return init_code_template.format(root_path=root_path)


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


def create_register_variable(variable):
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


def create_register_policy(policy, policies_folder):
    policy_name = clean(policy['name'])
    policy_code = parse_code(policy_name, policy['code'], policy.get('description', ''))
    policy_path = '{}/{}.py'.format(policies_folder, policy_name)

    with open(policy_path, 'w') as f:
        f.writelines(policy_code)

    # exec('from .policies.{p} import *'.format(p=policy_name))
    # policy = eval(policy_name)
    # policy.register()

    return {
        'name': policy_name,
        'value': {
            policy_name: {
                'type': policy_name
            }
        }
    }


def resource_name(resource, resource_type):
    return '{} [{}]'.format(resource['name'], resource_type)
