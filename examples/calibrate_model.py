import os
import spotpy
from spot_setup_merced import SpotSetup

dbname = "lake_mcclure_storage"
dbformat = "csv"

results = []
spot_setup = SpotSetup()
rep = 5

sampler = spotpy.algorithms.mcmc(spot_setup, dbformat=dbformat, dbname=dbname)
sampler.sample(rep)
results.append(sampler.getdata())
