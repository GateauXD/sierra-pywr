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
        # Parameters = Storage Values
        #              Violation Cost
        #              Hydrological Cost
        self.params = [spotpy.parameter.Uniform('mcClure_storage_value', -200, 100, 20),
                       spotpy.parameter.Uniform('mcSwain_storage_value', -200, 100, 20),
                       spotpy.parameter.Uniform('falls_storage_value', -200, 100, 20),
                       spotpy.parameter.Uniform('exchequer_violation_cost', -200, 100, 20),
                       spotpy.parameter.Uniform('below_crocker_inflow_violation_cost', -200, 100, 20),
                       spotpy.parameter.Uniform('mcSwain_PH_cost', -200, 100, 20),
                       spotpy.parameter.Uniform('falls_PH_cost', -200, 100, 20),
                       spotpy.parameter.Uniform('exchequer_PH_cost', -200, 100, 20),
                       ]
        self.evaluation_data = np.loadtxt("merced/s3_imports/Modifed_mcm_MERR.csv",
                                          skiprows=1, delimiter=',', usecols=[0])

    def parameters(self):
        # Generates a random param value based on the self.params
        return spotpy.parameter.generate(self.params)

    def simulation(self, vector):

        print("Trying parametre: {}".format(vector))

        # Create an array of parameters to pass to the model
        parameters = []
        for parameter in vector:
            parameters.append(parameter)

        # Simulate the model in another file simulation_run.py
        proc = subprocess.run(['python', 'simulation_run.py',
                               model_path, root_dir, bucket, network_key, str(parameters)], stdout=subprocess.PIPE)
        return np.load("merced/model_output.npy")

    def evaluation(self):
        # Returns the observed data
        return self.evaluation_data

    def objectivefunction(self, simulation, evaluation):
        evaluation_input = np.array([])
        # Get rid of the impact of NULL values in the evaluation data
        for index in range(0, len(simulation)):
            if not evaluation[index]:
                evaluation_input = np.append(evaluation_input, simulation[index])
            else:
                evaluation_input = np.append(evaluation_input, evaluation[index])
        # Generates a minimum objective value of the output
        objective_function = -rmse(evaluation=evaluation_input, simulation=simulation)

        print("Objective Value: {}".format(objective_function))
        return objective_function
