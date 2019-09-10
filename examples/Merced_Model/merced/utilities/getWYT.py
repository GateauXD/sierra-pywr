import datetime
import pandas as pd

SJVI_types = pd.read_csv("s3_imports/SJVI.csv", index_col=0, header=0, parse_dates=False,
                              squeeze=True)
start_time = datetime.datetime(1980, 10, 1)

def getWYT(timestep):
    for year in list(range(start_time.year, start_time.year + 33, 1)):
        if datetime.datetime(year, 10, 1) <= timestep.datetime <= datetime.datetime(year+1, 9, 30):
            return SJVI_types[year+1]

    return None
