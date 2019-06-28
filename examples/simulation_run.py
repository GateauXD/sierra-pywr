import os
import numpy as np
import sys
import json
from subprocess import Popen, PIPE

from tqdm import tqdm
from load_model import load_model

def evaluate_model(model_path, root_dir, bucket, network_key, parameter):
    # Changes JSON parameter to another value
    with open(model_path, "r") as f:
        data = json.load(f)

    data['parameters']['node/Lake McClure/Storage Value']['value'] = parameter

    with open(model_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Create the model with a modified JSON
    model = load_model(root_dir, model_path, bucket=bucket, network_key=network_key)

    # initialize model
    model.setup()

    timesteps = range(len(model.timestepper))
    step = None

    # Runs model through time to create a time series output
    for step in tqdm(timesteps, ncols=80):
        try:
            model.step()
        except Exception as err:
            print('Failed at step {}'.format(model.timestepper.current))
            print(err)
            break

    # Extract the model's output that we want to calibrate
    results = model.to_dataframe()
    results.to_csv('results.csv')

    results = results["node/Lake McClure/storage"]
    results = results.to_numpy()

    # Save time series data to a local file
    np.save("model_output.npy", results)

if __name__ == "__main__":
    # Saves passed in arguments as local variables
    model_path = sys.argv[1]
    root_dir = sys.argv[2]
    bucket = sys.argv[3]
    network_key = sys.argv[4]
    parameter = float(sys.argv[5])

    evaluate_model(model_path, root_dir, bucket, network_key, parameter)
