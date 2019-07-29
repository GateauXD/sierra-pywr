import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pywr.recorders import Recorder
from pywr.recorders.recorders import NodeRecorder
from scipy import interpolate
from parameters import WaterLPParameter
from utilities.converter import convert


class Lake_Mclure_Release_Policy(WaterLPParameter):
    """
    This Policy calculates the water releases from Lake Mclure to the hydropower facility
    and the flood control.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.args = args
        self.kwargs = kwargs
        self.esrd_table = pd.read_csv("policies/ESRD_unitsSI.csv", header=None)  # Units - meters and mcm
        self.elevation_conversion = pd.read_csv("policies/MERR_elev_vol_curve_unitsSI.csv")  # Units - meters and mcm
        self.yearly_types = pd.read_csv("s3_imports/WYT.csv", index_col=0, header=0, parse_dates=False,
                            squeeze=True)
        self.mid_northside = pd.read_csv("policies/MID_Northside_Diversion_cfs.csv", index_col=0, header=0, parse_dates=False,
                                  squeeze=True)  # Units - cfs
        self.mid_main = pd.read_csv("policies/MID_Main_Diversion_cfs.csv", index_col=0, header=0, parse_dates=False,
                                  squeeze=True)  # Units - cfs
        self.esrd_value = self.get_esrd()

    def value(self, timestep, scenario_index):
        curr_elevation = self.get_elevation(timestep)
        return_value = 0

        if curr_elevation < 192.6336:  # 632 ft
            return_value = self.min_release(timestep)

        elif curr_elevation > 192.6336 and self.is_conservation_zone(timestep, "<"):  # Between 632 ft and conservation zone
            return_value = self.conservation_release(timestep, scenario_index)

        elif self.is_conservation_zone(timestep, ">") and curr_elevation < 264.9779:  # Between conservation zone and 869.35 ft
            return_value = self.flood_control(timestep, scenario_index)

        elif curr_elevation < 264.9779 and curr_elevation < 269.4432:  # Between 869.35 ft and 884 ft
            return_value = self.surcharge(timestep, scenario_index)

        return convert(return_value, "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    def get_esrd(self):
        esrd_infow = self.esrd_table.iloc[0, 1:]
        esrd_elev = self.esrd_table.iloc[1:, 0]
        esrd_vals = self.esrd_table.iloc[1:, 1:]
        return interpolate.RectBivariateSpline(esrd_elev, esrd_infow, esrd_vals, kx=1, ky=1).fp

    def get_elevation(self, timestep):
        timestep = datetime(timestep.year, timestep.month, timestep.day)

        storage_recorder = self.model.recorders["node/Lake McClure/storage"].to_dataframe()
        elevation_value = self.elevation_conversion["Elevation (m)"]
        storage_value = self.elevation_conversion["Storage (mcm)"]

        if timestep == datetime(1980, 10, 1):
            initial_volume = self.model.nodes["Lake McClure [node]"].initial_volume
            return np.interp(initial_volume, storage_value, elevation_value)

        timestep = timestep - timedelta(1)
        volume_index = str(timestep.year) + "-" + str(timestep.month) + "-" + str(timestep.day)
        curr_volume = storage_recorder.loc[volume_index].get_values()[0]

        return np.interp(curr_volume, storage_value, elevation_value)

    def is_conservation_zone(self, timestep, operation):
        zones = {datetime(2000, 1, 1): 247.311672, datetime(2000, 3, 15): 247.311672, datetime(2000, 6, 15): 264.97788,
                 datetime(2000, 6, 30): 264.97788, datetime(2000, 7, 31): 262.89, datetime(2000, 8, 31): 259.2324,
                 datetime(2000, 9, 30): 252.984, datetime(2000, 10, 31): 247.311672}  # Units - meters
        date = datetime(2000, timestep.month, timestep.day)

        for index in range(0, len(zones.keys())):
            list_zones = list(zones.keys())
            # Floor function for the entries in the dict. Looks for the first value that is greater than our given date
            # Which means the dict value we are looking for is the one before.
            if date <= list_zones[index]:
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
        cfs_to_cms = 0.028316847
        type_value = self.yearly_types.loc[timestep.year]
        date = datetime(2000, timestep.month, timestep.day)

        # Dry Year
        if type_value == 1:
            zones = {datetime(2000, 1, 1): 60.0, datetime(2000, 4, 1): 60.0, datetime(2000, 6, 1): 15.0,
                     datetime(2000, 10, 16): 60.0, datetime(2000, 11, 1): 75.0}  # Units - cfs
        # Normal Year
        else:
            zones = {datetime(2000, 1, 1): 75.0, datetime(2000, 4, 1): 75.0, datetime(2000, 6, 1): 25.0,
                     datetime(2000, 10, 16): 75.0, datetime(2000, 11, 1): 100.0}  # Units - cfs

        for index in range(0, len(zones.keys())):
            list_zones = list(zones.keys())
            if date <= list_zones[index]:
                return zones[list_zones[index - 1]] * cfs_to_cms

        return zones[list_zones[-1]] * cfs_to_cms

    def conservation_release(self, timestep, scenario_index):
        return min(self.combined_release(timestep, scenario_index), 127.4258115) # Max of combined release or 4500 cfs

    def flood_control(self, timestep, scenario_index):
        return min(max(self.combined_release(timestep, scenario_index), self.get_esrd()), 169.901082)  # Max of combined release, ESRD release or 6500 cfs

    def surcharge(self, timestep, scenario_index):
        return max(self.combined_release(timestep, scenario_index), self.get_esrd())  # Max of combined release and ESRD release

    def combined_release(self, timestep, scenario_index):
        # Const to convert CFS to CMS
        cfs_to_cms = 0.028316847

        # Loading Data from IFRS and CSV files
        csv_index = str(timestep.month) + "/" + str(timestep.day) + "/" + str(timestep.year)
        # Obtain the CFS values
        # ifrs_value = Requirement_Merced_R_below_Crocker_Huffman_Dam.value(timestep, scenario_index)
        ifrs_value = self.model.recorders["node/Merced R below Crocker-Huffman Dam/requirement"].to_dataframe()
        ifrs_date = datetime(timestep.year, timestep.month, timestep.day)

        if ifrs_date == datetime(1980, 10, 1):
            ifrs_value = 0.061344  # Units - cms
        else:
            ifrs_date = ifrs_date - timedelta(1)
            ifrs_value = ifrs_value.loc[ifrs_date].get_values()[0]  # Units - cms

        northside_value = self.mid_northside.loc[csv_index]  # Units - cfs
        main_value = self.mid_main.loc[csv_index]  # Units - cfs

        # Convert the northside and main values from CFS to CMS
        northside_value = northside_value * cfs_to_cms
        main_value = main_value * cfs_to_cms

        return ifrs_value + northside_value + main_value

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)

Lake_Mclure_Release_Policy.register()
print(" [*] Lake_Mclure_Release_Policy successfully registered")
