import math
import pandas as pd
import numpy as np
from parameters import WaterLPParameter
from datetime import datetime, timedelta


class node_New_Melones_Reservoir_Storage_Value(WaterLPParameter):

    def _value(self, timestep, scenario_index):
        min_elevation = 182.87
        max_elevation = 341.05
        multiplier = self.model.parameters['melones_storageValueConstant'].value(timestep, scenario_index)
        leading_multiplier = self.model.parameters['melones_storage_value_leading'].value(timestep, scenario_index)
        return -1 * leading_multiplier * math.exp((multiplier * (max_elevation - min_elevation) / self.model.parameters["node/New Melones Lake/Elevation"].value(timestep, scenario_index)))

    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        data = {}
        return cls(model, **data)


node_New_Melones_Reservoir_Storage_Value.register()
print(" [*] node_New_Melones_Reservoir_Storage_Value successfully registered")
