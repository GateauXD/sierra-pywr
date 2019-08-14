import matplotlib.pyplot as plt
import pandas as pd
from pylab import rcParams

col_names = []
item_of_interest = "Lake McClure/storage"

def generate_csv():
    results_csv = pd.read_csv("climate_change.csv", skiprows=[1])
    return_csv = results_csv.filter(regex=item_of_interest)
    global col_names
    col_names = [col for col in results_csv.columns if item_of_interest in col]

    # Simplify the Column names
    for col_name in col_names:
        new_name = col_name.split("/")[0]
        return_csv.rename(columns={col_name: new_name}, inplace=True)

    return return_csv

graph_data = generate_csv()

rcParams['figure.figsize'] = 24, 12
fig = plt.figure()
ax = plt.gca()
plt.title("Climate Change Scenarios for Lake McClure Storage Value")
plt.ylabel("Storage Value (mcm)")
# for col_name in graph_data.columns:
#     graph_data.plot(kind="line", y=col_name, ax=ax)

graph_data.boxplot()
plt.show()
