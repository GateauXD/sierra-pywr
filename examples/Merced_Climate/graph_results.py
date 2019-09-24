import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import matplotlib.dates as mdates
import seaborn as sns

mean = True
date_of_interest = [2070,2100]
item_of_interest = "Lake McClure Inflow Flood Days"
climate_scenarios = ["CanESM2_rcp45", "CanESM2_rcp85", "CNRM-CM5_rcp45", "CNRM-CM5_rcp85", "HadGEM2-ES_rcp45",
                     "HadGEM2-ES_rcp85", "MIROC5_rcp45", "MIROC5_rcp85"]
climate_columns = []
for column_name in climate_scenarios:
    climate_columns.append(column_name + "/" + item_of_interest)
# cms_to_af = 810.714402
cms_to_af = 1

historic_csv = pd.read_csv("C:\\Users\\GateauXD\\Documents\\GitHub\\waterlp-pywr2-dan\\examples\\Merced_Model\\Graph.csv", index_col=[0])
climate_change_csv = pd.read_csv("Graph.csv", index_col=[0])
historic_csv.index = pd.to_datetime(historic_csv.index)
climate_change_csv.index = pd.to_datetime(climate_change_csv.index)
# Get date of interest
climate_change_csv = climate_change_csv.loc["{}-01-01".format(date_of_interest[0]):"{}-12-31".format(date_of_interest[1])]

if mean:
    # Overall Mean
    overall_historic = historic_csv.mean()
    overall_climate = climate_change_csv.mean()
    # Annual Means
    yearly_historic = historic_csv.groupby(historic_csv.index.year).mean()
    yearly_climate = climate_change_csv.groupby(climate_change_csv.index.year).mean()
    # Convert to Monthly Means over all Years
    monthly_historic = historic_csv.groupby(historic_csv.index.month).mean()
    monthly_climate = climate_change_csv.groupby(climate_change_csv.index.month).mean()
    # Convert Monthly to Quarterly mean
    quarter_historic = monthly_historic.groupby(np.arange(len(monthly_historic)) // 3).mean()
    quarter_climate = monthly_climate.groupby(np.arange(len(monthly_climate)) // 3).mean()
    # Swap quarters around so OND is first
    quarter_historic = quarter_historic.loc[[3, 0, 1, 2]]
    quarter_climate = quarter_climate.loc[[3, 0, 1, 2]]

    # Change units of flow from mcm to af
    quarter_historic[item_of_interest] = quarter_historic[item_of_interest] * cms_to_af
    for climate_scenario in climate_scenarios:
        quarter_climate[climate_scenario + "/" + item_of_interest] = quarter_climate[
                                                                         climate_scenario + "/" + item_of_interest] * cms_to_af

    # Get the Difference and Percent Difference from historic
    quarter_delta_change = pd.DataFrame()
    quarter_percent_change = pd.DataFrame()
    yearly_delta_change = pd.DataFrame()
    yearly_percent_change = pd.DataFrame()
    for climate_scenario in climate_scenarios:
        quarter_delta_change[climate_scenario] = (
                    quarter_climate[climate_scenario + "/" + item_of_interest] - quarter_historic[item_of_interest])
        quarter_percent_change[climate_scenario] = 100 * (
                    quarter_climate[climate_scenario + "/" + item_of_interest] - quarter_historic[item_of_interest]) / \
                                                   quarter_historic[item_of_interest]
        yearly_delta_change[climate_scenario] = (
                    yearly_climate[climate_scenario + "/" + item_of_interest] - yearly_historic[item_of_interest])
        yearly_percent_change[climate_scenario] = 100 * (
                    yearly_climate[climate_scenario + "/" + item_of_interest] - yearly_historic[item_of_interest]) / \
                                                  yearly_historic[item_of_interest]
# Flood Days
else:
    # Annual Sums
    yearly_historic = historic_csv.groupby(historic_csv.index.year).sum()
    yearly_climate = climate_change_csv.groupby(climate_change_csv.index.year).sum()
    # Overall Mean
    overall_historic = yearly_historic.mean()
    overall_climate = yearly_climate.mean()

plt.rcParams["figure.figsize"] = [50,35]
time = ["Near Future (2030-2060)", "Far Future (2070-2100)"]
index = 1
overall_climate = overall_climate[climate_columns]
overall_climate["Historic"] = overall_historic[item_of_interest]
overall_items = []
for item in climate_scenarios:
    overall_items.append(item + "/" + item_of_interest)

ax = quarter_climate.reset_index().plot(x="index", y=overall_items, kind="bar")
plt.xticks(np.arange(4), ("OND", "JFM", "AMJ", "JAS"), rotation=0, fontsize="54")
plt.yticks(fontsize="54")
plt.setp(ax.spines.values(), linewidth=3)
plt.setp(ax.get_legend().get_texts(), fontsize='54')
plt.title("Difference McSwain PH Hydropower Production " + time[index], fontsize='60')
plt.legend(climate_scenarios, fontsize='54')
plt.ylabel("Difference from Historic (MWD)", fontsize='54')
plt.xlabel("Quarter", fontsize='54')
plt.savefig("Figures/outflow_flood_averages_" + time[index].split()[0])

ax = quarter_delta_change.reset_index().plot(x="index", y=climate_scenarios, kind="bar")
plt.xticks(np.arange(4), ("OND", "JFM", "AMJ", "JAS"),rotation=0, fontsize="54")
plt.yticks(fontsize="54")
plt.setp(ax.spines.values(), linewidth=3)
plt.setp(ax.get_legend().get_texts(), fontsize='54')
plt.title("Difference McSwain PH Hydropower Production " + time[index], fontsize='60')
plt.legend(climate_scenarios, fontsize='54')
plt.ylabel("Difference from Historic (MWD)", fontsize='54')
plt.xlabel("Quarter", fontsize='54')
plt.savefig("Figures/outflow_flood_difference_" + time[index].split()[0])

ax = quarter_percent_change.reset_index().plot(x="index",y=climate_scenarios, kind="bar")
plt.xticks(np.arange(4), ("OND", "JFM", "AMJ", "JAS"),rotation=0, fontsize="54")
plt.setp(ax.spines.values(), linewidth=3)
plt.yticks(fontsize="54")
plt.title("Percent Difference McSwain PH Hydropower Production " + time[index], fontsize='60')
plt.legend(climate_scenarios, fontsize='54')
plt.ylabel("Percent Difference (%)", fontsize='54')
plt.xlabel("Quarter", fontsize='54')
plt.savefig("Figures/outflow_flood_percent_" + time[index].split()[0])

quarter_climate.to_csv("merced/s3_imports/quarter_avg.csv")
yearly_climate.to_csv("merced/s3_imports/yearly_avg.csv")
