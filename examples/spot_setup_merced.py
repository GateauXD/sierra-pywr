import os
import spotpy
import numpy as np
import json
import subprocess

from subprocess import PIPE
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
        self.params = [spotpy.parameter.Uniform('storage_cost', -500, 500, 100)]
        self.evaluation_data = np.loadtxt("merced/s3_imports/Modifed_mcm_MERR.csv", skiprows=1, delimiter=',', usecols=[1])

    def parameters(self):
        # Generates a random param value based on the self.params
        return spotpy.parameter.generate(self.params)

    def simulation(self, vector):
        # Simulate the model in another file simulation_run.py
        proc = subprocess.run(['python', 'simulation_run.py', model_path, root_dir, bucket, network_key, str(vector[0])]
                                , stdout=subprocess.PIPE)
        return np.load("merced/model_output.npy")

    def evaluation(self):
        # Returns the observed data
        return self.evaluation_data

    def objectivefunction(self, simulation, evaluation):
        # Generates a minimum objective value of the output
        objectivefunction = -rmse(evaluation=evaluation, simulation=simulation)
        return objectivefunction
