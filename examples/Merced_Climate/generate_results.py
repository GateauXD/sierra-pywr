import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np

reservoirs = ["node/Lake McClure/storage", "node/Lake McClure/observed storage"]
powerhouses = ["node/New Exchequer PH/Fixed head", "node/New Merced Falls PH/Fixed head", "node/New McSwain PH/Fixed head"]
powerhouse_flows = ["MERCE-L-CON3 [link]", "Merced PH Inflow", "McSwain PH Inflow"]
ph_gauge = ["node/Lake McClure Inflow/flow", "MERCE-L-CON2 [link]", "MERCE-L-CON4 [link]", "node/Near Stevinson_11272500/flow"]
ifrs = ["node/blwNewExchequerPH/flow", "node/Merced R below Crocker-Huffman Dam/flow", "Lake McClure Flood Control [node]"]
ifrs_req = ["node/blwNewExchequerPH/requirement", "node/Merced R below Crocker-Huffman Dam/requirement", "node/Lake McClure Flood Control [node]/requirement"]


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

def change_season(month):
    if month in [1,2,3]:
        return 1
    elif month in [4,5,6]:
        return 2
    elif month in [7,8,9]:
        return 3
    else:
        return 4

def generate_csv_climate():
    global reservoirs
    global powerhouses
    global ph_gauge
    # Generate Hydropower Generation
    water_density = 1000
    gravity = 9.81
    efficiency = 0.9
    mcm_to_cms = 1000000 / (24 * 3600)

    climate_scenarios = ["CanESM2_rcp45", "CanESM2_rcp85", "CNRM-CM5_rcp45", "CNRM-CM5_rcp85", "HadGEM2-ES_rcp45",
                         "HadGEM2-ES_rcp85", "MIROC5_rcp45", "MIROC5_rcp85"]
    climate_change_scenarios = pd.read_csv("climate_change.csv", index_col=[0])
    return_csv = pd.DataFrame()
    return_csv["Recorder"] = climate_change_scenarios[climate_scenarios[1] + "/Recorder"]
    return_csv["WYT_Year_Type"] = climate_change_scenarios[climate_scenarios[0] + "/WYT_Year_Type"]
    return_csv["Water_Year"] = climate_change_scenarios[climate_scenarios[0] + "/Water_Year"]
    for climate_scenario in climate_scenarios:
        results_csv = climate_change_scenarios.filter(regex=climate_scenario)

        return_csv[climate_scenario + "/Lake McClure Storage"] = results_csv[
                                                                     climate_scenario + "/node/Lake McClure/storage"] * 0.81071318210885

        # 1 Inflow to McClure
        return_csv[climate_scenario + "/Lake McClure Inflow"] = (
                results_csv[climate_scenario + "/node/Lake McClure Inflow/flow"] * mcm_to_cms)
        # 2 Outflow from Merced Basin
        return_csv[climate_scenario + "/node/Basin Outflow/flow"] = results_csv[
                                                                        climate_scenario + "/node/Near Stevinson_11272500/flow"] * 0.81071318210885
        # 3 Flood days Out of Lake McClure
        return_csv[climate_scenario + "/Lake McClure Outflow Flood Days"] = ((results_csv[
                                                                                  climate_scenario + "/MERCE-L-CON2 [link]"] +
                                                                              results_csv[
                                                                                  climate_scenario + "/MERCE-L-CON4 [link]"]) > 15.9).astype(
            int)
        # Flood days Into Lake McClure
        return_csv[climate_scenario + "/Lake McClure Inflow Flood Days"] = (
                    (results_csv[climate_scenario + "/node/Lake McClure Inflow/flow"] * mcm_to_cms) > 14.68).astype(int)

        # 5 No. of days IRFs not being met
        for index, value in enumerate(ifrs):
            # Sum up time the IFR did not pass
            return_csv[climate_scenario + "/" + value + "/ifr_not_met"] = (
                        results_csv[climate_scenario + "/" + ifrs_req[index]] - results_csv[
                    climate_scenario + "/" + ifrs[index]] > 0.0001).astype(int)

        # 6 Total HP production (MWH)
        return_csv[climate_scenario + "/Hydropower Production"] = 0
        for index, powerhouse in enumerate(powerhouses):
            return_csv[climate_scenario + "/Hydropower Production"] = return_csv[
                                                                          climate_scenario + "/Hydropower Production"] + \
                                                                      (efficiency * water_density * gravity * \
                                                                       results_csv[climate_scenario + "/" + powerhouse] \
                                                                       * results_csv[
                                                                           climate_scenario + "/" + powerhouse_flows[
                                                                               index]] / 3600)
    return return_csv

def generate_csv_historic():
    global reservoirs
    global powerhouses
    global ph_gauge
    # Generate Hydropower Generation
    water_density = 1000
    gravity = 9.81
    efficiency = 0.9
    mcm_to_cms = 1000000 / (24 * 3600)

    columns = ["Recorder", "Release Requirement", "WYT_Year_Type", "Water_Year"]
    columns = columns + reservoirs + powerhouses + powerhouse_flows + ph_gauge + ifrs + ifrs_req

    results_csv = pd.read_csv("merced/results.csv", skiprows=[1])
    wyt_csv = pd.read_csv("merced/s3_imports/WYT.csv", index_col=[0])
    results_csv = results_csv[columns].copy()
    return_csv = results_csv[
        ["Recorder", "node/Lake McClure/storage", "node/Lake McClure/observed storage", "WYT_Year_Type",
         "Water_Year"]].copy()
    return_csv["Lake McClure Storage"] = results_csv["node/Lake McClure/storage"] * 0.81071318210885
    # 1 Inflow to McClure
    return_csv["Lake McClure Inflow"] = (results_csv["node/Lake McClure Inflow/flow"] * mcm_to_cms)
    # 2 Outflow from Merced Basin
    return_csv["node/Basin Outflow/flow"] = results_csv["node/Near Stevinson_11272500/flow"] * 0.81071318210885
    # 3 Flood days Out of Lake McClure
    return_csv["Lake McClure Outflow Flood Days"] = (
                (results_csv["MERCE-L-CON2 [link]"] + results_csv["MERCE-L-CON4 [link]"]) > 15.9).astype(int)
    # 4 Flood Days Into Lake McClure
    return_csv["Lake McClure Inflow Flood Days"] = (
                (results_csv["node/Lake McClure Inflow/flow"] * mcm_to_cms) > 14.68).astype(int)
    # 5 No. of days IRFs not being met
    for index, value in enumerate(ifrs):
        # Sum up time the IFR did not pass
        return_csv[value + "/ifr_not_met"] = (results_csv[ifrs_req[index]] - results_csv[ifrs[index]] > 0.0001).astype(
            int)
    # 6 Total HP production (MWH)
    return_csv["Hydropower Production"] = 0
    for index, powerhouse in enumerate(powerhouses):
        return_csv["Hydropower Production"] = return_csv["Hydropower Production"] + (
                    efficiency * water_density * gravity * results_csv[powerhouse] \
                    * results_csv[powerhouse_flows[index]] / 3600)

    return return_csv

def graph_files(climate_change_csv , historic_csv):
    pd.options.mode.chained_assignment = None
    results_hist_csv = historic_csv
    results_climate_csv = climate_change_csv

    for index in range(0,4):
        ## Storage
        if index == 0:
            modify_results_hist_csv = results_hist_csv.iloc[:, [0, 2, 3]]
            results_climate_csv_45 = results_climate_csv.iloc[:, [0, 2, 3, 21, 39, 57]]
            results_climate_csv_85 = results_climate_csv.iloc[:, [0, 2, 12, 30, 48, 66]]
            file_name = "Storage"
            y_label = "Volume (TAF)"
            y_lim_low = 0
            y_lim_high = 1200
        ##Inflow
        if index == 1:
            modify_results_hist_csv = results_hist_csv.iloc[:,[0,2,6]]
            results_climate_csv_45 = results_climate_csv.iloc[:,[0,2,4,22,40,58]]
            results_climate_csv_85 = results_climate_csv.iloc[:,[0,2,13,31,49,67]]
            file_name = "Inflow"
            y_label = "Discharge (TAF)"
            y_lim_low = 0
            y_lim_high = 1500
        ##Outflow
        if index == 2:
            modify_results_hist_csv = results_hist_csv.iloc[:,[0,2,7]]
            results_climate_csv_45 = results_climate_csv.iloc[:,[0,2,5,23,41,59]]
            results_climate_csv_85 = results_climate_csv.iloc[:,[0,2,14,32,50,68]]
            file_name = "Outflow"
            y_label = "Discharge (TAF)"
            y_lim_low = 0
            y_lim_high = 300
        ##HP Production
        if index == 3:
            modify_results_hist_csv = results_hist_csv.iloc[:, [0, 2, 13]]
            results_climate_csv_45 = results_climate_csv.iloc[:, [0, 2, 11, 29, 47, 65]]
            results_climate_csv_85 = results_climate_csv.iloc[:, [0, 2, 20, 38, 56, 74]]
            file_name = "HP"
            y_label = "HP Production (MWh)"
            y_lim_low = 0
            y_lim_high = 40000

        modify_results_hist_csv.columns = ['Date', 'WY', 'Historic']
        modify_results_hist_csv['Month'] = pd.DatetimeIndex(modify_results_hist_csv['Date']).month
        modify_results_hist_csv['Day'] = pd.DatetimeIndex(modify_results_hist_csv['Date']).dayofyear

        modify_results_hist_csv["WYT_Month"] = modify_results_hist_csv["Month"].apply(lambda x: change_month(x))
        modify_results_hist_csv["WYT_Season"] = modify_results_hist_csv["WYT_Month"].apply(lambda x: change_season(x))

        results_hist_csv_melt = pd.melt(modify_results_hist_csv,
                                        id_vars=["Date", "WY", "Month", "WYT_Month", "WYT_Season"],
                                        value_vars=["Historic"],
                                        var_name=["Scen"],
                                        value_name="Values"
                                        )

        results_climate_csv_45.columns = ['Date', 'WY', 'CanESM2', 'CNRM-CM5', 'HadGEM2', 'MIROC5']
        results_climate_csv_85.columns = ['Date', 'WY', 'CanESM2', 'CNRM-CM5', 'HadGEM2', 'MIROC5']
        results_climate_csv_45["Date"] = pd.to_datetime(results_climate_csv_45["Date"])
        results_climate_csv_85["Date"] = pd.to_datetime(results_climate_csv_85["Date"])

        results_climate_csv_45['Month'] = results_climate_csv_45["Date"].dt.month
        results_climate_csv_85['Month'] = results_climate_csv_85["Date"].dt.month

        results_climate_csv_45["WYT_Month"] = results_climate_csv_45["Month"].apply(lambda x: change_month(x))
        results_climate_csv_85["WYT_Month"] = results_climate_csv_85["Month"].apply(lambda x: change_month(x))
        results_climate_csv_45["WYT_Season"] = results_climate_csv_45["WYT_Month"].apply(lambda x: change_season(x))
        results_climate_csv_85["WYT_Season"] = results_climate_csv_85["WYT_Month"].apply(lambda x: change_season(x))

        results_climate_csv_melt_45 = pd.melt(results_climate_csv_45,
                                              id_vars=["Date", "WY", "Month", "WYT_Month", "WYT_Season"],
                                              value_vars=['CanESM2', 'CNRM-CM5', 'HadGEM2', 'MIROC5'],
                                              var_name=["Scen"],
                                              value_name="Values"
                                              )
        results_climate_csv_melt_85 = pd.melt(results_climate_csv_85,
                                              id_vars=["Date", "WY", "Month", "WYT_Month", "WYT_Season"],
                                              value_vars=['CanESM2', 'CNRM-CM5', 'HadGEM2', 'MIROC5'],
                                              var_name=["Scen"],
                                              value_name="Values"
                                              )
        graph_data_45 = pd.concat([results_hist_csv_melt, results_climate_csv_melt_45])
        graph_data_85 = pd.concat([results_hist_csv_melt, results_climate_csv_melt_85])

        plt_color = ["#505050", "#c1f215", "#00cdcd", "#ffa500", "#c6b6e0"]
        sns.set(style="whitegrid", rc={'figure.figsize': (20.7, 13.27)}, font_scale=2.0)
        plt.rcParams["figure.figsize"] = [16, 9]
        sns.boxplot(data=graph_data_45, x="WYT_Month", y="Values", hue="Scen", palette=plt_color)
        # sns.lineplot(x="Day", y="Values", hue="Scen", data=graph_data_45, palette=plt_color)
        # plt.xticks(np.arange(4), ["OND", "JFM", "AMJ", "JAS"])
        plt.xticks(np.arange(12), ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"])
        plt.xlabel("Monthly")
        plt.ylabel(y_label)
        plt.ylim(y_lim_low, y_lim_high)
        plt.savefig("Figures/" + file_name + "_BoxMonthly_45.png")
        # plt.savefig("Figures/" + file_name + "_LineMonthly_45.png")
        plt.clf()

        plt.rcParams["figure.figsize"] = [16, 9]
        sns.boxplot(data=graph_data_85, x="WYT_Month", y="Values", hue="Scen", palette=plt_color)
        # sns.lineplot(x="Day", y="Values", hue="Scen", data=graph_data_85, palette=plt_color)
        # plt.xticks(np.arange(4), ["OND", "JFM", "AMJ", "JAS"])
        plt.xticks(np.arange(12), ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"])
        plt.xlabel("Monthly")
        plt.ylabel(y_label)
        plt.ylim(y_lim_low, y_lim_high)
        plt.savefig("Figures/" + file_name + "_BoxMonthly_85.png")
        # plt.savefig("Figures/"+ file_name + "_LineMonthly_85.png")
        plt.clf()

        sns.boxplot(data=graph_data_45, x="WYT_Season", y="Values", hue="Scen", palette=plt_color)
        # sns.lineplot(x="Day", y="Values", hue="Scen", data=graph_data_45, palette=plt_color)
        plt.xticks(np.arange(4), ["OND", "JFM", "AMJ", "JAS"])
        plt.xlabel("Quarter")
        plt.ylabel(y_label)
        plt.ylim(y_lim_low, y_lim_high)
        plt.savefig("Figures/" + file_name + "_BoxQuarter_45.png")
        # plt.savefig("Figures/" + file_name + "_LineMonthly_45.png")
        plt.clf()

        plt.rcParams["figure.figsize"] = [16, 9]
        sns.boxplot(data=graph_data_85, x="WYT_Season", y="Values", hue="Scen", palette=plt_color)
        # sns.lineplot(x="Day", y="Values", hue="Scen", data=graph_data_85, palette=plt_color)
        plt.xticks(np.arange(4), ["OND", "JFM", "AMJ", "JAS"])
        plt.xlabel("Quarter")
        plt.ylabel(y_label)
        plt.ylim(y_lim_low, y_lim_high)
        plt.savefig("Figures/" + file_name + "_BoxQuarter_85.png")
        # plt.savefig("Figures/"+ file_name + "_LineMonthly_85.png")
        plt.clf()

climate_change_csv = generate_csv_climate()
historic_csv = generate_csv_historic()
graph_files(climate_change_csv, historic_csv)