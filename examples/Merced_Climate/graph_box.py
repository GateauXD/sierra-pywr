import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np


def change_month(month):
    if month == 10:
        return 1
    elif month == 11:
        return 2
    elif month == 12:
        return 3
    elif month == 1:
        return 4
    elif month == 2:
        return 5
    elif month == 3:
        return 6
    elif month == 4:
        return 7
    elif month == 5:
        return 8
    elif month == 6:
        return 9
    elif month == 7:
        return 10
    elif month == 8:
        return 11
    else:
        return 12
seasonal = True
pd.options.mode.chained_assignment = None
results_hist_csv = pd.read_csv(r"Graph_Historic.csv", index_col= None)
results_climate_csv = pd.read_csv(r"Graph_Climate.csv", index_col= None)
###########################
## Storage
results_hist_csv = results_hist_csv.iloc[:,[0,2,3]]
results_climate_csv_45 = results_climate_csv.iloc[:,[0,2,3,21,39,57]]
results_climate_csv_85 = results_climate_csv.iloc[:,[0,2,12,30,48,66]]
file_name = "Storage"
y_label = "Volume (TAF)"
y_lim_low = 0
y_lim_high = 1200
##Inflow
# results_hist_csv = results_hist_csv.iloc[:,[0,2,6]]
# results_climate_csv_45 = results_climate_csv.iloc[:,[0,2,4,22,40,58]]
# results_climate_csv_85 = results_climate_csv.iloc[:,[0,2,13,31,49,67]]
# file_name = "Inflow"
# y_label = "Discharge (TAF)"
# y_lim_low = 0
# y_lim_high = 1500
##Outflow
# results_hist_csv = results_hist_csv.iloc[:,[0,2,7]]
# results_climate_csv_45 = results_climate_csv.iloc[:,[0,2,5,23,41,59]]
# results_climate_csv_85 = results_climate_csv.iloc[:,[0,2,14,32,50,68]]
# file_name = "Outflow"
# y_label = "Discharge (TAF)"
# y_lim_low = 0
# y_lim_high = 300
##HP Production
# results_hist_csv = results_hist_csv.iloc[:,[0,2,13]]
# results_climate_csv_45 = results_climate_csv.iloc[:,[0,2,11,29,47,65]]
# results_climate_csv_85 = results_climate_csv.iloc[:,[0,2,20,38,56,74]]
# file_name = "HP"
# y_label = "HP Production (MWh)"
# y_lim_low = 0
# y_lim_high = 40000
###########################


results_hist_csv.columns = ['Date','WY','Historic']
results_hist_csv['Month'] = pd.DatetimeIndex(results_hist_csv['Date']).month
results_hist_csv['Day'] = pd.DatetimeIndex(results_hist_csv['Date']).dayofyear

results_hist_csv["WYT_Month"] = results_hist_csv["Month"].apply(lambda x: change_month(x))

results_hist_csv_melt = pd.melt(results_hist_csv,
                          id_vars=["Date", "WY", "Month", "WYT_Month", "Day"],
                          value_vars=["Historic"],
                          var_name=["Scen"],
                          value_name="Values"
                          )

results_climate_csv_45.columns = ['Date','WY','CanESM2','CNRM-CM5','HadGEM2','MIROC5']
results_climate_csv_85.columns = ['Date','WY','CanESM2','CNRM-CM5','HadGEM2','MIROC5']
results_climate_csv_45['Month'] = pd.DatetimeIndex(results_climate_csv_45['Date']).month
results_climate_csv_45['Day'] = pd.DatetimeIndex(results_climate_csv_45['Date']).dayofyear
results_climate_csv_85['Month'] = pd.DatetimeIndex(results_climate_csv_85['Date']).month
results_climate_csv_85['Day'] = pd.DatetimeIndex(results_climate_csv_85['Date']).dayofyear

results_climate_csv_45["WYT_Month"] = results_climate_csv_45["Month"].apply(lambda x: change_month(x))
results_climate_csv_85["WYT_Month"] = results_climate_csv_85["Month"].apply(lambda x: change_month(x))



results_climate_csv_melt_45 = pd.melt(results_climate_csv_45,
                          id_vars=["Date", "WY", "Month", "WYT_Month","Day"],
                          value_vars=['CanESM2','CNRM-CM5','HadGEM2','MIROC5'],
                          var_name=["Scen"],
                          value_name="Values"
                          )
results_climate_csv_melt_85 = pd.melt(results_climate_csv_85,
                          id_vars=["Date", "WY", "Month", "WYT_Month", "Day"],
                          value_vars=['CanESM2','CNRM-CM5','HadGEM2','MIROC5'],
                          var_name=["Scen"],
                          value_name="Values"
                          )
graph_data_45 = pd.concat([results_hist_csv_melt,results_climate_csv_melt_45])
graph_data_85 = pd.concat([results_hist_csv_melt,results_climate_csv_melt_85])

if seasonal:
    # Seasonal
    graph_data_45 = graph_data_45.groupby(graph_data_45["WYT_Month"]).mean()
    graph_data_45 = graph_data_45.groupby(np.arange(len(graph_data_45)) // 3).mean()
    graph_data_85 = graph_data_85.groupby(graph_data_85["WYT_Month"]).mean()
    graph_data_85 = graph_data_85.groupby(np.arange(len(graph_data_85)) // 3).mean()


plt_color = ["#505050", "#c1f215", "#00cdcd", "#ffa500", "#c6b6e0"]
sns.set(style="whitegrid", rc={'figure.figsize': (20.7, 13.27)}, font_scale=2.0)
plt.rcParams["figure.figsize"] = [16,9]
pp = sns.boxplot(x="index", y="Values", hue="Scen", data=graph_data_45,palette=plt_color)
# sns.lineplot(x="Day", y="Values", hue="Scen", data=graph_data_45, palette=plt_color)
plt.xticks(np.arange(4), ["OND", "JFM", "AMJ", "JAS"])
plt.xlabel("Quarter")
plt.ylabel(y_label)
plt.ylim(y_lim_low, y_lim_high)
plt.savefig("Figures/"+ file_name + "_BoxQuarter_45.png")
# plt.savefig("Figures/" + file_name + "_LineMonthly_45.png")
plt.clf()

plt.rcParams["figure.figsize"] = [16,9]
sns.boxplot(data=graph_data_85.reset_index(), x="index", y="Values", hue="Scen",palette=plt_color)
# sns.lineplot(x="Day", y="Values", hue="Scen", data=graph_data_85, palette=plt_color)
plt.xticks(np.arange(4), ["OND", "JFM", "AMJ", "JAS"])
plt.xlabel("Quarter")
plt.ylabel(y_label)
plt.ylim(y_lim_low, y_lim_high)
plt.savefig("Figures/"+ file_name + "_BoxQuarter_85.png")
# plt.savefig("Figures/"+ file_name + "_LineMonthly_85.png")

#sns.lineplot(x="Day", y="Values", hue="Scen",estimator=None, lw=1, data=graph_data, legend=False)

