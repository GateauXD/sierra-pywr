import os
import spotpy
from spot_setup_merced import SpotSetup


results = []
spot_setup = SpotSetup()
rep = 5
dbname = "lake_mcclure_storage"
dbformat = "csv"



sampler = spotpy.algorithms.mcmc(spot_setup, dbformat=dbformat, dbname=dbname, save_sim=True)
sampler.sample(rep)
results.append(sampler.getdata())
