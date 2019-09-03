import matplotlib.pyplot as plt
import pandas as pd
import math
import numpy as np
import matplotlib.dates as mdates
import seaborn as sns


historic_csv = pd.read_csv("Graph.csv", index_col=[0])


plt.rcParams["figure.figsize"] = [50,30]

ax = sns.kdeplot(historic_csv['node/Lake McClure/storage'], cumulative=True, vertical=True)
sns.kdeplot(historic_csv["node/Lake McClure/observed storage"], cumulative=True, vertical=True, ax=ax)
plt.xticks(fontsize="25")
plt.legend(fontsize="25")
plt.setp(ax.spines.values(), linewidth=3)
plt.yticks(fontsize="25")
plt.title("Daily Average McSwain PH Hydropower Production ", fontsize='35')
plt.ylabel("Hydropower Production (MWD)", fontsize='30')
plt.xlabel("Quarter", fontsize='40')

plt.show()
