import spotpy
from spot_setup_merced import SpotSetup

# Set local storage variables for calibration ie: Name and Format(CSV, RAM)
dbname = "temp_db"
dbformat = "csv"

rep = 50
results = []
spot_setup = SpotSetup()

# Setup the environment with a markov chain monte carlo algorithm
sampler = spotpy.algorithms.lhs(spot_setup, dbformat=dbformat, dbname=dbname)

# Calibrate the model over "rep" iterations
sampler.sample(rep)
results.append(sampler.getdata())
