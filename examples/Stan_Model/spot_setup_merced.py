import os
import spotpy
import pandas as pd
import numpy as np
import subprocess

from spotpy.objectivefunctions import nashsutcliffe, rmse

root_dir = os.path.join(os.getcwd(), 'Stan_Model')
bucket = 'openagua-networks'
model_path = os.path.join(root_dir, 'pywr_model.json')
network_key = os.environ.get('NETWORK_KEY')

class SpotSetup(object):

    def parameters(self):
        # Generates a random param value based on the self.params
        return spotpy.parameter.generate(self.params)

    def __init__(self, used_algorithm='default'):
        self.used_algorithm = used_algorithm
        # Generating Parameter Values via CSV
        parameters_csv = pd.read_csv("Stan_Model/input_csvs/parameters.csv")
        self.params = []
        for index in range(0, len(parameters_csv)):
            self.params.append(spotpy.parameter.Uniform(parameters_csv.iloc[index, 0],
                                                        parameters_csv.iloc[index, 1],
                                                        parameters_csv.iloc[index, 2],
                                                        parameters_csv.iloc[index, 3]))
        del parameters_csv

        # Generating Evaluation Data via CSV
        evaluation_csv = pd.read_csv("Stan_Model/input_csvs/evaluation.csv")
        results = pd.read_csv("Stan_Model/results.csv")
        self.evaluation_data = np.array(results[evaluation_csv.iloc[0]][1:])
        for index in range(1, len(evaluation_csv)):
            self.evaluation_data = np.concatenate((self.evaluation_data, np.array(results[evaluation_csv.iloc[index]][1:])),axis=1)
        del evaluation_csv, results

    def simulation(self, vector):

        print("Trying parametre: {}".format(vector))

        # Create an array of parameters to pass to the model
        parameters = []
        for parameter in vector:
            parameters.append(parameter)

        # Simulate the model in another file simulation_run.py
        proc = subprocess.run(['python', 'simulation_run.py',
                               model_path, root_dir, bucket, network_key, str(parameters)], stdout=subprocess.PIPE)
        simulation_data = np.load("Stan_Model/model_output.npy").T
        return_data = []
        for index in range(0, len(simulation_data)):
            return_data.append(simulation_data[index])

        return return_data
    def evaluation(self):
        # Returns the observed data
        return_data = []

        for index in range(0, self.evaluation_data.shape[1]):
            return_data.append((self.evaluation_data[:, index]))

        return return_data

    def objectivefunction(self, simulation, evaluation):
        # Get rid of the impact of NULL values in the evaluation data
        for i in range(0, len(evaluation)):
            for j, value in enumerate(evaluation[i]):
                if not evaluation[i][j]:
                    evaluation[i][j] = simulation[i][j]

        # Generate the multiple objective functions =
        objective_values = []
        for index in range(0, len(evaluation)-1):
            objective_values.append(nashsutcliffe(evaluation=evaluation[index], simulation=simulation[index]))

        print("Objective Value: {}".format(objective_values))
        return objective_values
