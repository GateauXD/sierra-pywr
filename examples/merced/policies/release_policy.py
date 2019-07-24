import numpy as np
import pandas as pd
from datetime import datetime
from pywr.recorders import Recorder
from pywr.recorders.recorders import NodeRecorder
from scipy import interpolate
from parameters import WaterLPParameter
from .IFRs import Requirement_Merced_R_below_Crocker_Huffman_Dam


class Lake_Mclure_Release_Policy(WaterLPParameter):
    """
    This Policy calculates the water releases from Lake Mclure to the hydropower facility
    and the flood control.
    """

    # Get volume of the reservoir and convert the that to elevation
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.const_values = self.get_constant_values()
        self.esrd_value = self.get_esrd()

    def value(self, timestep, scenario_index):
        curr_elevation = self.get_elevation(timestep)

        if curr_elevation < 632:
            return self.min_release(timestep)

        elif curr_elevation > 632 and self.is_conservation_zone(timestep):
            return self.conservation_release(timestep, scenario_index)

        elif self.is_conservation_zone(timestep) and curr_elevation < 869.35:
            return self.flood_control(timestep, scenario_index)

        elif curr_elevation < 869.35 and curr_elevation < 884:
            return self.surcharge(timestep, scenario_index)

        raise ValueError("Elevation does not fit in the ranges")

    def get_esrd(self):
        esrd_table = pd.read_csv("policies/ESRD_unitsSI.csv", header=None)
        esrd_infow = esrd_table.iloc[0, 1:]
        esrd_elev = esrd_table.iloc[1:, 0]
        esrd_vals = esrd_table.iloc[1:, 1:]
        return interpolate.RectBivariateSpline(esrd_elev, esrd_infow, esrd_vals, kx=1, ky=1)

    def get_elevation(self, timestep):
        storage_recorder = self.model.recorders["node/Lake McClure/storage"].to_dataframe()
        elevation_conversion = pd.read_csv("policies/MERR_elev_vol_curve_unitsSI.csv")
        elevation_value = elevation_conversion["Elevation (m)"]
        storage_value = elevation_conversion["Storage (mcm)"]

        volume_index = str(timestep.year) + "-" + str(timestep.month) + "-" + str(timestep.day)
        curr_volume = storage_recorder.loc[volume_index].get_values()[0]

        return np.interp(curr_volume, storage_value, elevation_value)

    def is_conservation_zone(self, timestep, operation):
        zones = {datetime(2000, 1, 1): 811.39, datetime(2000, 3, 15): 811.39, datetime(2000, 6, 15): 869.35, datetime(2000, 6, 30): 869.35, datetime(2000, 7, 31): 862.5, datetime(2000, 8, 31): 850.5,
                 datetime(2000, 9, 30): 830.0, datetime(2000, 10, 31): 811.39}
        date = datetime(2000, timestep.month, timestep.day)

        for index in range(1, len(zones.keys())):
            list_zones = list(zones.keys())
            # Floor function for the entries in the dict. Looks for the first value that is greater than our given date
            # Which means the dict value we are looking for is the one before.
            if list_zones[index] < date:
                curr_elevation = self.get_elevation(timestep)
                zone_value = zones[list_zones[index-1]]
                if operation == "<":
                    return curr_elevation < zone_value
                elif operation == ">":
                    return curr_elevation > zone_value
                else:
                    raise TypeError("Invalid Operation Input")
        return False

    def min_release(self, timestep):
        # Yearly_Types == Dry or Normal year
        yearly_types = pd.read_csv("s3_imports/WYT.csv", index_col=0, header=0, parse_dates=False,
                                   squeeze=True)
        type_value = yearly_types.loc[timestep.year]
        date = datetime(2000, timestep.month, timestep.day)

        # Dry Year
        if type_value == 1:
            zones = {datetime(2000, 1, 1): 60.0, datetime(2000, 4, 1): 60.0, datetime(2000, 6, 1): 15.0,
                     datetime(2000, 10, 16): 60.0, datetime(2000, 11, 1): 75.0}
        # Normal Year
        else:
            zones = {datetime(2000, 1, 1): 75.0, datetime(2000, 4, 1): 75.0, datetime(2000, 6, 1): 25.0,
                     datetime(2000, 10, 16): 75.0, datetime(2000, 11, 1): 100.0}

        for index in range(1, len(zones.keys())):
            list_zones = list(zones.keys())
            if list_zones[index] < date:
                return zones[list_zones[index - 1]]

        return zones[list_zones[-1]]

    def conservation_release(self, timestep, scenario_index):
        return max(self.combined_release(timestep, scenario_index), 4500)

    def flood_control(self, timestep, scenario_index):
        return max(self.combined_release(timestep, scenario_index), self.get_esrd(), 6000)

    def surcharge(self, timestep, scenario_index):
        return max(self.combined_release(timestep, scenario_index) ,self.get_esrd())

    def combined_release(self, timestep, scenario_index):
        # Const to convert CFS to CMS
        cfs_to_cms = 0.028316847

        # Loading Data from IFRS and CSV files
        csv_index = str(timestep.year) + "-" + str(timestep.month) + "-" + str(timestep.day)
        below_crocker_class = Requirement_Merced_R_below_Crocker_Huffman_Dam()
        mid_northside = pd.read_csv("policies/MID_Northside_Diversion_cfs.csv", index_col=0, header=0, parse_dates=False,
                                  squeeze=True)
        mid_main = pd.read_csv("policies/MID_Main_Diversion_cfs.csv", index_col=0, header=0, parse_dates=False,
                                  squeeze=True)

        # Obtain the CFS values
        ifrs_value = below_crocker_class.value(timestep, scenario_index)
        northside_value = mid_northside.loc[csv_index]
        main_value = mid_main.loc[csv_index]

        # Convert the northside and main values from CFS to CMS
        northside_value = northside_value * cfs_to_cms
        main_value = main_value * cfs_to_cms

        return ifrs_value + northside_value + main_value

    def get_constant_values(self):
        # Modified Function from initializationDataUsed_HECRes.py
        # :return: Dict with constant values
        return_dict = {}

        # pre-accumulated Mar-Oct min release volumes (acre-feet) by Year Type
        marOctMinReleaseVolume = {1: 22711, 2: 16810}
        return_dict["marOctMinReleaseVolume"] = marOctMinReleaseVolume

        # Minimum downstream flow (cfs) from FERC License
        FERCminFlowTable = {
            1: {1: 75, 2: 75, 3: 75, 4: 75, 5: 75, 6: 25, 7: 25, 8: 25, 9: 25, 10: 25, 11: 100, 12: 100},
            2: {1: 60, 2: 60, 3: 60, 4: 60, 5: 60, 6: 15, 7: 15, 8: 15, 9: 15, 10: 15, 11: 75, 12: 75},
        }
        return_dict["FERCminFlowTable"] = FERCminFlowTable

        # cumulative from Mar 1, Apr 1, May 1, and Jun 1 through Jun 30 (acre-feet)
        cumulativeMinReleaseTable = {
            1: {3: 15174, 4: 10562, 5: 6099, 6: 1488},
            2: {3: 11841, 4: 8152, 5: 4582, 6: 892},
        }
        return_dict["cumulativeMinReleaseTable"] = cumulativeMinReleaseTable

        # Fall Fishery Release in cfs applied evenly from Oct 15 to Oct 31
        return_dict["fallFisheryRelease"] = 371

        # snowmelt scaler by month
        SnowScaler = {3: 0.5, 4: 1.0, 5: 1.0, 6: 1.0}
        return_dict["SnowScaler"] = SnowScaler

        # constants
        return_dict["cfsToAcFt"] = 3600.0 / 43560.0
        return_dict["daysToJun30"] = {3: 122, 4: 91, 5: 61, 6: 30}
        return_dict["daysInMonth"] = {3: 31, 4: 30, 5: 31, 6: 30}
        return_dict["fallFisheryReleaseVolume"] = 12500.0
        return_dict["minPool"] = 115000.0
        return_dict["storageBuffer"] = 20000.0
        return_dict["snowstorageBuffer"] = 20000.0
        return_dict["evaporation"] = 20000.0

        # set demand multiplier on first timestep of the run
        return_dict["defaultMultiplier"] = 1.0

        return return_dict

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)

Lake_Mclure_Release_Policy.register()
print(" [*] Lake_Mclure_Release_Policy successfully registered")
