import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

date_of_interest = [1980,2060]
item_of_interest = "Lake McClure Inflow/flow"

def generate_csv():
    results_csv = pd.read_csv("MERR_inflow_LakeMcClure_RCP45.csv", index_col=[4])
    results_csv = results_csv.loc["{}-10".format(date_of_interest[0]):"{}-9".format(date_of_interest[1])]
    graph_melt = pd.melt(results_csv,
                         id_vars=["Year", "Scen", "Month"],
                         value_vars=["Inflow"],
                         value_name="values"
                         )
    return graph_melt


index = 0
time = ["Near Future (2030-2060)", "Far Future (2070-2100)"]
graph_data = generate_csv()

plt.rcParams["figure.figsize"] = [16,9]
sns.set(style="whitegrid", rc={'figure.figsize': (20.7, 13.27)}, font_scale=1.5)
sns.boxplot(x="Month", y="values", hue="Scen", data=graph_data)
plt.title("Lake McClure Monthly Inflow - All Scenarios RCP 4.5 - {}".format(time[index]))
plt.xlabel("Month")
plt.ylabel(r"Flow Value (million $m^{3}$)")
plt.savefig("Figures/{}_monthly_inflow_all_4.5.png".format(time[index].split()[0].lower()))
