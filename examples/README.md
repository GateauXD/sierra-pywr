# Calibration of Hydrological Models + Running Climate Change Scenrios

The goal of this project was to efficently calibrate hydrological networkx models utilizing optimization techniques. I used Spotpy for the optimization alogrithms and intergrated into the pywr ecosystem.

### Relevant Files
1. [Script to run any climate change scenrios](https://github.com/GateauXD/waterlp-pywr2/blob/master/examples/run_climate_change.py)
2. [Parent script to start calibration](https://github.com/GateauXD/waterlp-pywr2/blob/master/examples/Merced_Model/calibrate_model.py)
3. [Bulk of the calibration code with parameter setup, iterating the model, comparing results through a loss function, and tweaking parameters](https://github.com/GateauXD/waterlp-pywr2/blob/master/examples/Merced_Model/spot_setup_merced.py)
4. [Script that runs the model with modified parameters and formats the outputs](https://github.com/GateauXD/waterlp-pywr2/blob/master/examples/Merced_Model/run_merced_model.py)
5. [CSVs used in choosing parameters nodes and their value ranges](https://github.com/GateauXD/waterlp-pywr2/tree/master/examples/Merced_Model/merced/input_csvs)

### Results:

When we I was put onto this project claibration was done by hand and took a long time to get correct. A calibrated model of Merced's model is shown below. 
![Calibrated Results](https://raw.githubusercontent.com/GateauXD/waterlp-pywr2/master/examples/Merced_Model/Figures/Lake%20McClure%20Storage%20Value.png)
