import os
import sys
from pywr.core import Model
from importlib import import_module
from tqdm import tqdm
import matplotlib.pyplot as plt


def load_model(root_dir, model_path, bucket=None, network_key=None, check_graph=False):
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
    model = Model.load(model_path, path=model_path)
    return model
