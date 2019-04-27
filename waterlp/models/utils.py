import re


def clean(s):
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '', s)

    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '', s)

    return s


spaces = '\n' + ' ' * 8

policy_code_template = """from ..parameters import WaterLPParameter


class {policy_name}(WaterLPParameter):
    \"\"\"{policy_description}\"\"\"

    def value(self, timestep, scenario_index):

        {policy_code} 

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
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
    if 'return ' not in lines[-1]:
        lines[-1] = 'return ' + lines[-1]
    new_code = spaces.join(lines)

    policy_str = policy_code_template.format(
        policy_name=policy_name,
        policy_description=description,
        policy_code=new_code
    )

    return policy_str


def create_register_policy(policy, policies_folder):

    policy_name = clean(policy['name'])
    policy_code = parse_code(policy_name, policy['code'], policy.get('description', ''))
    policy_path = '{}/{}.py'.format(policies_folder, policy_name)

    with open(policy_path, 'w') as f:
        f.writelines(policy_code)

    exec('from .policies.{p} import {p}'.format(p=policy_name))
    policy = eval(policy_name)
    policy.register()

    return {
        'name': policy_name,
        'value': {policy_name: {'type': policy_name}}
    }


def resource_name(resource, resource_type):
    return '{} [{}]'.format(resource['name'], resource_type)
