import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pywr.recorders import Recorder
from pywr.recorders.recorders import NodeRecorder
from parameters import WaterLPParameter
from datetime import date

class Lake_Mclure_Release_Policy(WaterLPParameter):
    """
    This Policy calculates the water releases from Lake Mclure to the hydropower facility
    and the flood control.
    """

    # Get volume of the reservoir and convert the that to elevation
    def __init__(self):
        self.elevation_conversion = pd.read_csv("examples/merced/policies/MERR_elev_vol_curve_unitsSI.csv")
        self.elevation_value = self.elevation_conversion["Elevation (m)"]
        self.storage_value = self.elevation_conversion["Storage (mcm)"]
        self.curr_volume = self.model.recorders["node/Lake McSwain/storage"].values()

    def get_elevation(self):
        return np.interp(self.curr_volume, self.storage_value, self.elevation_value)

    def is_conservation_zone(self, timestep, operation):
        zones = {datetime(2000, 1, 1): 811.39, datetime(2000, 3, 15): 811.39, datetime(2000, 6, 15): 869.35, datetime(2000, 6, 30): 869.35, datetime(2000, 7, 31): 862.5, datetime(2000, 8, 31): 850.5,
                 datetime(2000, 9, 30): 830.0, datetime(2000, 10, 31): 811.39}
        date = datetime(2000, timestep.month, timestep.day)

        for index in range(1, len(zones.keys())):
            list_zones = list(zones.keys())
            # Floor function for the entries in the dict. Looks for the first value that is greater than our given date
            # Which means the dict value we are looking for is the one before.
            if list_zones[index] < date:
                curr_elevation = self.get_elevation()
                zone_value = zones[list_zones[index-1]]
                if operation == "<":
                    return curr_elevation < zone_value
                elif operation == ">":
                    return curr_elevation > zone_value
                else:
                    raise TypeError("Invalid Operation Input")
        return False

    def value(self, timestep):
        curr_elevation = self.get_elevation()

        if curr_elevation < 632:
            return self.min_release(timestep)

        elif curr_elevation > 632 and self.is_conservation_zone(timestep):
            return self.conservation_release()

        elif self.is_conservation_zone(timestep) and curr_elevation < 869.35:
            return self.flood_control()

        elif curr_elevation < 869.35 and curr_elevation < 884:
            return self.surcharge()

        raise ValueError("Elevation does not fit in the rages")

    def min_release(self, timestep):
        # Yearly_Types == Dry or Normal year
        yearly_types = pd.read_csv("examples/merced/s3_imports/WYT.csv", index_col=0, header=0, parse_dates=False,
                                   squeeze=True)
        type_value = yearly_types.loc[[str(timestep.year), "livneh_historical"]]
        date = datetime(2000, timestep.month, timestep.day)
        zones = {}

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

        raise LookupError("Invalid TimeStep")

    def conservation_release(self):
        pass

    def flood_control(self):
        pass

    def surcharge(self):
        pass


# Lake_Mclure_Release_Policy.register()
# print(" [*] Lake_Mclure_Release_Policy successfully registered")
