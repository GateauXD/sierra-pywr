import pandas as pd
import numpy as np

reservoirs = ["node/Lake McClure/storage", "node/Lake McClure/observed storage"]
powerhouses = ["node/New Exchequer PH/Fixed head", "node/New Merced Falls PH/Fixed head", "node/New McSwain PH/Fixed head"]
powerhouse_flows = ["MERCE-L-CON3 [link]", "Merced PH Inflow", "McSwain PH Inflow"]
ph_gauge = ["node/Lake McClure Inflow/flow", "MERCE-L-CON2 [link]", "MERCE-L-CON4 [link]", "node/Near Stevinson_11272500/flow"]
# date_of_interest = ["10/1/1980", "1/10/2006"]
ifrs = ["node/blwNewExchequerPH/flow", "node/Merced R below Crocker-Huffman Dam/flow", "Lake McClure Flood Control [node]"]
ifrs_req = ["node/blwNewExchequerPH/requirement", "node/Merced R below Crocker-Huffman Dam/requirement", "node/Lake McClure Flood Control [node]/requirement"]

def generate_csv():
    global reservoirs
    global powerhouses
    global ph_gauge
    # Generate Hydropower Generation
    water_density = 1000
    gravity = 9.81
    efficiency = 0.9
    mcm_to_cms = 1000000/(24*3600)

    columns = ["Recorder", "Release Requirement"]
    columns = columns + reservoirs + powerhouses + powerhouse_flows + ph_gauge + ifrs + ifrs_req

    results_csv = pd.read_csv("merced/results.csv", skiprows=[1])
    wyt_csv = pd.read_csv("merced/s3_imports/WYT.csv", index_col=[0])
    results_csv = results_csv[columns].copy()
    return_csv = results_csv[["Recorder", "node/Lake McClure/storage", "node/Lake McClure/observed storage"]].copy()

    # 1 Inflow to McClure
    return_csv["Lake McClure Inflow"] = (results_csv["node/Lake McClure Inflow/flow"] * mcm_to_cms)
    # 2 Outflow from Merced Basin
    return_csv["node/Basin Outflow/flow"] = results_csv["node/Near Stevinson_11272500/flow"] * mcm_to_cms
    # 3 Flood days Out of Lake McClure
    return_csv["Lake McClure Outflow Flood Days"] = ((results_csv["MERCE-L-CON2 [link]"] + results_csv["MERCE-L-CON4 [link]"]) > 15.9).astype(int)
    # 4 Flood Days Into Lake McClure
    return_csv["Lake McClure Inflow Flood Days"] = ((results_csv["node/Lake McClure Inflow/flow"] * mcm_to_cms) > 14.68).astype(int)
    # 5 No. of days IRFs not being met
    for index, value in enumerate(ifrs):
        # Sum up time the IFR did not pass
        return_csv[value + "/ifr_not_met"] = (results_csv[ifrs_req[index]] - results_csv[ifrs[index]] > 0.0001).astype(int)
        # # Sort by monthly and sum up the truth values
        # ifr_csv = results_csv[["Recorder", "ifr_not_met"]].copy()
        # ifr_csv["Recorder"] = pd.to_datetime(ifr_csv['Recorder'])
        # ifr_csv.set_index(ifr_csv.Recorder, inplace=True)
        # ifr_csv.drop("Recorder", axis=1, inplace=True)
        # ifr_csv = ifr_csv.groupby(pd.Grouper(freq="M")).apply(lambda x: x.astype(int).sum())
        #
        # rcParams['figure.figsize'] = 24, 12
        # fig = plt.figure()
        # ax = plt.gca()
        # fig.add_subplot(ifr_csv.plot(kind='bar', y="ifr_not_met", ax=ax))
        # ax.xaxis.set_major_locator(ticker.MultipleLocator(4))
        # plt.title("{} IFR".format(ifrs[index].split("/")[1]))
        # plt.ylabel("Occurrences")
    # 6 Total HP production (MWH)
    for index, powerhouse in enumerate(powerhouses):
        return_csv[powerhouse.split("/")[1] + "/Hydropower Production"] = efficiency * water_density * gravity * results_csv[powerhouse] \
                                                                   * results_csv[powerhouse_flows[index]] / 3600

    return_csv.to_csv("Graph.csv")


graph_data = generate_csv()
