import matplotlib.pyplot as plt
import pandas as pd
import math
import numpy as np
import matplotlib.dates as mdates
import seaborn as sns


historic_csv = pd.read_csv("Stan_Model/results.csv", index_col=[0])


plt.rcParams["figure.figsize"] = [50,30]
items_of_interest = ["node/New Melones Lake/storage", "node/Beardsley Reservoir/storage", "node/Donnells Reservoir/storage",
                     "node/New Spicer Meadow Reservoir/storage", "node/Pinecrest Reservoir/storage", "node/Relief Reservoir/storage",
                     "node/Tulloch Lake/storage"]


for item in items_of_interest:
    ax = plt.gca()
    observed_name = "observed " + item.split('/')[-1]
    observed_name_list = item.split('/')
    observed_name_list[-1] = observed_name
    observed_name = "/".join(observed_name_list)

    historic_csv.plot(kind='line', y=item, ax=ax)
    historic_csv.plot(kind='line', y=observed_name, ax=ax)
    plt.savefig("figure/" + observed_name_list[-2])
    plt.clf()
