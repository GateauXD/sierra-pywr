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
        self.curr_volume = self.model.recorders["node/Lake McClure/storage"].to_dataframe()
        self.const_values = self.get_constant_values()

    def get_elevation(self, timestep):
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
                curr_elevation = self.get_elevation(timestep)
                zone_value = zones[list_zones[index-1]]
                if operation == "<":
                    return curr_elevation < zone_value
                elif operation == ">":
                    return curr_elevation > zone_value
                else:
                    raise TypeError("Invalid Operation Input")
        return False

    def value(self, timestep):
        curr_elevation = self.get_elevation(timestep)

        if curr_elevation < 632:
            return self.min_release(timestep)

        elif curr_elevation > 632 and self.is_conservation_zone(timestep):
            return self.conservation_release(timestep)

        elif self.is_conservation_zone(timestep) and curr_elevation < 869.35:
            return self.flood_control(timestep)

        elif curr_elevation < 869.35 and curr_elevation < 884:
            return self.surcharge(timestep)

        raise ValueError("Elevation does not fit in the rages")

    def min_release(self, timestep):
        # Yearly_Types == Dry or Normal year
        yearly_types = pd.read_csv("examples/merced/s3_imports/WYT.csv", index_col=0, header=0, parse_dates=False,
                                   squeeze=True)
        type_value = yearly_types.loc[[str(timestep.year), "livneh_historical"]]
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

        raise LookupError("Invalid TimeStep")

    def conservation_release(self, timestep):
        # TODO Add conditional for combined or 4500 cfs
        return self.combined_release(timestep)

    def flood_control(self, timestep):
        # TODO Add conditional for combined or 6000 cfs or Maxed ESRD
        return self.combined_release(timestep)

    def surcharge(self, timestep):
        # TODO Add conditional for combined or Maxed ESRD
        return self.combined_release(timestep)

    def stevension_multiplier(self, timestep):
        date = datetime(2000, timestep.month, timestep.day)

        if datetime == datetime(2000, 3, 1):
            fall_fish = self.const_values["fallFisheryRelease"]
            evaporation_volume = self.const_values["evaporation"]
            storage_buffer = self.const_values["storageBuffer"]
            min_pool_volume = self.const_values["minPool"]
            infow = pd.read_csv()
            loss_to_gw = pd.read_csv()
            min_release = pd.read_csv()
            cowell_diversion = pd.read_csv()
            merced_nwr_demand = pd.read_csv()
            stevinson_demand = pd.read_csv()
            # TODO Get data from Feb28
            storage_volume = self.curr_volume
            storage_june_15th = self.curr_volume

            water_supply_forecast = storage_volume + infow - min_release - cowell_diversion - merced_nwr_demand \
                                    - fall_fish - evaporation_volume - min_pool_volume - storage_buffer - loss_to_gw

            north_side_demand = pd.read_csv()
            merced_id_demand = pd.read_csv()
            elnido_id_demand = pd.read_csv()

            if storage_june_15th < 289000:
                multiplier = max(min(water_supply_forecast
                                                                    / (north_side_demand + merced_id_demand + stevinson_demand + 0.5 * elnido_id_demand), 1), 0)
                self.const_values["stevinson_multiplier"] = multiplier
                return self.const_values["stevinson_multiplier"], multiplier
            else:
                multiplier = max(min(((water_supply_forecast - stevinson_demand)/north_side_demand +
                                      merced_id_demand + 0.5 * elnido_id_demand), 1), 0)
                self.const_values["stevinson_multiplier"] = 1
                return self.const_values["stevinson_multiplier"],
        else:
            if "stevinson_multiplier" in self.const_values.keys():
                return self.const_values["stevinson_multiplier"], self.const_values["defaultMultiplier"]

            else:
                self.const_values["stevinson_multiplier"] = self.const_values["defaultMultiplier"]
                return self.const_values["stevinson_multiplier"], self.const_values["stevinson_multiplier"]

    def snow_release(self, timestep):
        date = datetime(2000, timestep.month, timestep.year)

        if date.month == datetime(2000, 3, 1).month or date.month == datetime(2000, 4, 1).month \
                or date.month == datetime(2000, 5, 1).month or date.month == datetime(2000, 6, 1).month:
            total_inflow = pd.read_csv()
            min_release = {}
            mercedid_demand = pd.read_csv("MercedID")
            mercedwr_demand = pd.read_csv("MercedNWR")
            stevinsonwd_demand = pd.read_csv("StevinsonWD")
            elnidoid_demand = pd.read_csv("ElNidoID")
            cads_demand = pd.read_csv("CADs")

            # Add function to calculate all these values at the same time till JUNE

            total_demand = mercedid_demand + mercedwr_demand + stevinsonwd_demand + elnidoid_demand + 0.5 * cads_demand

            # Dry or Normal
            yearly_types = pd.read_csv("examples/merced/s3_imports/WYT.csv", index_col=0, header=0, parse_dates=False,
                                       squeeze=True)
            type_value = yearly_types.loc[[str(timestep.year), "livneh_historical"]]

            if type_value == 1:
                min_release = {3: 15174, 4: 10562, 5: 6099, 6: 1488}
            else:
                min_release = {3: 11841, 4: 8152, 5: 4582, 6: 892}

            depletion_to_shaffer = pd.read_csv()

            # Calculate Available Space S = FloodControl_StoreZone - PoolStore - snow storage buffer
            available_space = 0

            spill = total_inflow - total_demand - min_release - depletion_to_shaffer - available_space

            days_till_june = (datetime(2000, 6, 30) - date).days
            return spill/days_till_june

        return 0

    def combined_release(self, timestep):
        date = datetime(2000, timestep.month, timestep.day)

        if datetime(2000, 3, 1) < date < datetime(2000, 10, 31):
            northside_demand = pd.read_csv()
            merced_id_demand = pd.read_csv()
            elnido_id_demand = pd.read_csv()
        else:
            northside_demand = 0
            merced_id_demand = 0
            elnido_id_demand = 0

        mercedwr_demand = pd.read_csv("MercedNWR")
        stevinsonwd_demand = pd.read_csv("StevinsonWD")
        depletion_to_shaffer = pd.read_csv()
        cads_demand = pd.read_csv("CADs")
        mcclure_min_release = pd.read_csv()

        if datetime(2000, 2, 1) < date < datetime(2000, 7, 1):
            scaler_values = {datetime(2000, 3, 1).month: 0.5,datetime(2000, 4, 1).month: 1.0, datetime(2000, 5, 1).month: 1.0, datetime(2000, 6, 1).month: 1.0 }
            scaler_value = scaler_values[date.month]
        else:
            scaler_value = 0

        snowmelt_release = self.snow_release(timestep) * scaler_value
        (mutiplier, stevinson_multiplier) = self.stevension_multiplier(timestep)
        return mutiplier * (northside_demand + merced_id_demand + 0.5 * elnido_id_demand) + mercedwr_demand \
               + stevinson_multiplier + stevinsonwd_demand + cads_demand + depletion_to_shaffer + mcclure_min_release \
               + snowmelt_release

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

# Lake_Mclure_Release_Policy.register()
# print(" [*] Lake_Mclure_Release_Policy successfully registered")
