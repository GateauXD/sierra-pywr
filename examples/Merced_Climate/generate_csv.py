import pandas as pd
import numpy as np

reservoirs = ["node/Lake McClure/storage", "node/Lake McClure/observed storage"]
powerhouses = ["node/New Exchequer PH/Fixed head", "node/New Merced Falls PH/Fixed head", "node/New McSwain PH/Fixed head"]
powerhouse_flows = ["MERCE-L-CON3 [link]", "Merced PH Inflow", "McSwain PH Inflow"]
ph_gauge = ["node/Lake McClure Inflow/flow", "MERCE-L-CON2 [link]", "MERCE-L-CON4 [link]", "node/Near Stevinson_11272500/flow"]
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

    climate_scenarios = ["CanESM2_rcp45", "CanESM2_rcp85", "CNRM-CM5_rcp45", "CNRM-CM5_rcp85", "HadGEM2-ES_rcp45",
                      "HadGEM2-ES_rcp85", "MIROC5_rcp45", "MIROC5_rcp85"]
    climate_change_scenarios = pd.read_csv("climate_change.csv", index_col=[0])
    return_csv = pd.DataFrame()
    return_csv["Recorder"] = climate_change_scenarios[climate_scenarios[0] + "/Recorder"]
    for climate_scenario in climate_scenarios:
        results_csv = climate_change_scenarios.filter(regex=climate_scenario)

        # 1 Inflow to McClure
        return_csv[climate_scenario + "/Lake McClure Inflow"] = (
                    results_csv[climate_scenario + "/node/Lake McClure Inflow/flow"] * mcm_to_cms)
        # 2 Outflow from Merced Basin
        return_csv[climate_scenario + "/node/Basin Outflow/flow"] = results_csv[climate_scenario + "/node/Near Stevinson_11272500/flow"] * mcm_to_cms
        # 3 Flood days Out of Lake McClure
        return_csv[climate_scenario + "/Lake McClure Outflow Flood Days"] = ((results_csv[climate_scenario + "/MERCE-L-CON2 [link]"] + results_csv[climate_scenario + "/MERCE-L-CON4 [link]"]) > 15.9).astype(int)
        # Flood days Into Lake McClure
        return_csv[climate_scenario + "/Lake McClure Inflow Flood Days"] = ((results_csv[climate_scenario + "/node/Lake McClure Inflow/flow"] * mcm_to_cms) > 14.68).astype(int)

        # 5 No. of days IRFs not being met
        for index, value in enumerate(ifrs):
            # Sum up time the IFR did not pass
            return_csv[climate_scenario + "/" + value + "/ifr_not_met"] = (results_csv[climate_scenario + "/" + ifrs_req[index]] - results_csv[climate_scenario + "/" + ifrs[index]] > 0.0001).astype(int)

        # 6 Total HP production (MWH)
        for index, powerhouse in enumerate(powerhouses):
            return_csv[climate_scenario + "/" + powerhouse.split("/")[1] + "/Hydropower Production"] = efficiency * water_density * gravity * \
                                                                              results_csv[climate_scenario + "/" +powerhouse] \
                                                                              * results_csv[
                                                                                  climate_scenario + "/" + powerhouse_flows[index]] /3600

    return_csv.to_csv("Graph.csv")
    return return_csv

graph_data = generate_csv()

# columns = ["Recorder", "Release Requirement"]
# columns = columns + reservoirs + powerhouses + powerhouse_flows + ph_gauge + ifrs + ifrs_req
#
# results_csv = pd.read_csv("merced/results.csv", skiprows=[1])
# results_csv = results_csv[columns].copy()
# return_csv = results_csv[["Recorder", "node/Lake McClure/storage", "node/Lake McClure/observed storage"]].copy()
#
# # 1 Inflow to McClure
# return_csv["Lake McClure Inflow"] = (results_csv["node/Lake McClure Inflow/flow"] * mcm_to_cms)
# # 2 Outflow from Merced Basin
# return_csv["node/Basin Outflow/flow"] = results_csv["node/Near Stevinson_11272500/flow"] * mcm_to_cms
# # 3 Flood days
# return_csv["Flood Days"] = (results_csv["MERCE-L-CON2 [link]"] + results_csv["MERCE-L-CON4 [link]"]) > 15.9
# # 4 No. of days IRFs not being met
# for index, value in enumerate(ifrs):
#     # Sum up time the IFR did not pass
#     return_csv[value + "/ifr_not_met"] = (results_csv[ifrs_req[index]] - results_csv[ifrs[index]] > 0.0001)
#
# # 5 Total HP production (MWH)
# for index, powerhouse in enumerate(powerhouses):
#     return_csv[powerhouse.split("/")[1] + "/Hydropower Production"] = efficiency * water_density * gravity * \
#                                                                       results_csv[powerhouse] \
#                                                                       * results_csv[
#                                                                           powerhouse_flows[index]] * 3600 / 1000000
#
# return_csv.to_csv("Graph.csv")