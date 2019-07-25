import os
import spotpy
from spot_setup_merced import SpotSetup

# Set local storage variables for calibration ie: Name and Format(CSV, RAM)
dbname = "lake_mcclure_storage"
dbformat = "csv"

rep = 4
results = []
spot_setup = SpotSetup()

# Setup the environment with a markov chain monte carlo algorithm
sampler = spotpy.algorithms.mcmc(spot_setup, dbformat=dbformat, dbname=dbname)

# Calibrate the model over "rep" iterations
sampler.sample(rep)
results.append(sampler.getdata())
