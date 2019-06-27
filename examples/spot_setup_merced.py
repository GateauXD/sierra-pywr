import os
import spotpy
import numpy as np
import json

from tqdm import tqdm
from spotpy.parameter import Uniform
from spotpy.objectivefunctions import rmse
from load_model import load_model


root_dir = os.path.join(os.getcwd(), 'merced')
bucket = 'openagua-networks'
model_path = os.path.join(root_dir, 'pywr_model.json')
network_key = os.environ.get('NETWORK_KEY')

class SpotSetup(object):

    def __init__(self, used_algorithm='default'):
        self.used_algorithm = used_algorithm
        self.params = [spotpy.parameter.Uniform('storage_cost', -1000000, -20, 100000)]
        self.evaulation_data = np.loadtxt("merced/s3_imports/Modifed_mcm_MERR.csv", skiprows=1, delimiter=',', usecols=[1])

    def parameters(self):
        return spotpy.parameter.generate(self.params)

    def simulation(self, vector):

        print("Trying Parameter Value: {}".format(vector[0]))
        # Changes the parameter.
        with open(model_path, "r") as f:
            data = json.load(f)

        data['parameters']['node/Lake McClure/Storage Value']['value'] = vector[0]

        with open(model_path, 'w') as f:
            json.dump(data, f, indent=2)

        #Create the model with a modified JSON
        model = load_model(root_dir, model_path, bucket=bucket, network_key=network_key)

        # initialize model
        model.setup()

        timesteps = range(len(model.timestepper))
        step = None

        for step in tqdm(timesteps, ncols=80):
            try:
                model.step()
            except Exception as err:
                print('Failed at step {}'.format(model.timestepper.current))
                print(err)
                break

        # Extract the model output that we want to calibrate
        results = model.to_dataframe()
        results.to_csv('results.csv')

        del model

        results = results["node/Lake McClure/storage"]
        results = results.to_numpy()

        print("First Output {}".format(results[0]))
        return results

    def evaluation(self):
        return self.evaulation_data

    def objectivefunction(self, simulation, evaluation):
        # return a given list of a model simulation andobservation.
        objectivefunction = rmse(evaluation=evaluation, simulation=simulation)
        return objectivefunction
