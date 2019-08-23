import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import seaborn as sns

date_of_interest = [2030, 2060]
item_of_interest = "Lake McClure Inflow/flow"

historic_csv = pd.read_csv("C:\\Users\\GateauXD\\Documents\\GitHub\\waterlp-pywr2-dan\\examples\\Merced_Model\\Graph.csv")
climate_change_csv = pd.read_csv("Graph.csv")

plt.rcParams["figure.figsize"] = [16,9]

time = ["Near Future (2030-2060)", "Far Future (2070-2100)"]
index = 0

