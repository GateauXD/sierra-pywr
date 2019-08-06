import os
import sys
import pandas as pd
from pywr.core import Model
from importlib import import_module
from tqdm import tqdm


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
        except Exception as err:
            print(' [-] WARNING: {} could not be imported from {}'.format(name, package))
            print(type(err))
            print(err)

    # Step 2: Load and run model
    ret = Model.load(model_path, path=model_path)
    return ret


root_dir = os.path.join(os.getcwd(), 'stanislaus_demo')
bucket = 'openagua-networks'
model_path = os.path.join(root_dir, 'pywr_model.json')
network_key = os.environ.get('NETWORK_KEY')
model = load_model(root_dir, model_path, bucket=bucket, network_key=network_key)

# initialize model
model.setup()

timesteps = range(len(model.timestepper))
step = None

# run model
# note that tqdm + step adds a little bit of overhead.
# use model.run() instead if seeing progress is not important
path = 's3://{}/{}/'.format(bucket, network_key) + 'Scenarios/Livneh/energy_netDemand.csv'
energy_data = pd.read_csv(path, usecols=[0,1,2,3], index_col=0, header=None, names=['day','TotDemand','MaxDemand','MinDemand'], parse_dates=False)

for step in tqdm(timesteps, ncols=80):
    try:
        model.step()
    except Exception as err:
        print('Failed at step {}'.format(model.timestepper.current))
        print(err)
        break

# save results to CSV
results = model.to_dataframe()
results.to_csv('results.csv')

# # plot Lake McClure storage
# fig, ax = plt.subplots(figsize=(16, 8))
# S = results['node/Lake McClure/storage']
# ax.plot(S.index, S)
# fig.show()
