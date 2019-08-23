import math
import pandas as pd
import numpy as np
from parameters import WaterLPParameter
from datetime import datetime, timedelta


class node_Beardsley_Reservoir_Storage_Value(WaterLPParameter):

    def _value(self, timestep, scenario_index):
        multiplier = self.model.parameters['storageValueConstant'].value(timestep, scenario_index)
        leading_multiplier = self.model.parameters['storage_value_leading'].value(timestep, scenario_index)
        current_elevation = self.model.parameters["node/Beardsley Reservoir/Elevation"].value(timestep, scenario_index)
        max_elevation = self.model.parameters["node/Beardsley Reservoir/Storage Capacity"].value(timestep, scenario_index)
        min_elevation = self.model.parameters["node/Beardsley Reservoir/Inactive Pool"].value(timestep, scenario_index)

        return leading_multiplier * math.exp(multiplier * (max_elevation - current_elevation)/(max_elevation-min_elevation))

    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)


node_Beardsley_Reservoir_Storage_Value.register()
print(" [*] node_Beardsley_Reservoir_Storage_Value successfully registered")
