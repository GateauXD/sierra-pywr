import numpy as np
import pandas as pd
from hydroeval import *

# Change this to check parameter ex: ""
model_parameters = ["node/Below Merced Falls Dam/flow", "node/Near Stevinson_11272500/flow",
                    "node/MERCED R A POHONO BRIDGE NR YOSEMITE CA_11266500/flow",
                    "node/Lake McClure/storage"]

for model_parameter in model_parameters:
    # Generate the observed parameter name
    split_value = model_parameter.split("/")
    split_value[-1] = "observed " + split_value[-1]
    observed_parameter = "/".join(split_value)

    # Getting parameter values and changing them to numpy
    results_csv = pd.read_csv("merced/results.csv", skiprows=[1])
    model_data = results_csv[model_parameter].values
    observed_data = results_csv[observed_parameter].values

    # Calculate the metrics
    nse_value = float(evaluator(nse, model_data, observed_data))
    print("The NSE value of {} is : {}".format(model_parameter, nse_value))
    p_bias = float(evaluator(pbias, model_data, observed_data))
    print("The Percent Bias of {} is : {}".format(model_parameter, p_bias))
