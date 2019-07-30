import math
import pandas as pd
import numpy as np
from parameters import WaterLPParameter
from datetime import datetime, timedelta

elevation_conversion = pd.read_csv("policies/MERR_elev_vol_curve_unitsSI.csv")  # Units - meters and mcm


class node_Lake_McClure_Storage_Value(WaterLPParameter):

    def _value(self, timestep, scenario_index):
        multiplier = self.model.parameters['storageValueConstant'].value(timestep, scenario_index)
        curr_elevation = self.get_elevation(timestep)

        return -0.003 * math.exp(multiplier * (254 / curr_elevation))

    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    def get_elevation(self, timestep):
        timestep = datetime(timestep.year, timestep.month, timestep.day)

        storage_recorder = self.model.recorders["node/Lake McClure/storage"].to_dataframe()
        elevation_value = elevation_conversion["Elevation (m)"]
        storage_value = elevation_conversion["Storage (mcm)"]

        if timestep == datetime(1980, 10, 1):
            initial_volume = self.model.nodes["Lake McClure [node]"].initial_volume
            return np.interp(initial_volume, storage_value, elevation_value)

        timestep = timestep - timedelta(1)
        volume_index = str(timestep.year) + "-" + str(timestep.month) + "-" + str(timestep.day)
        curr_volume = storage_recorder.loc[volume_index].get_values()[0]

        return np.interp(curr_volume, storage_value, elevation_value)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)


node_Lake_McClure_Storage_Value.register()
print(" [*] node_Lake_McClure_Storage_Value successfully registered")
