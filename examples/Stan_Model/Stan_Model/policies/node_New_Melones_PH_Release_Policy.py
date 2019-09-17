import math
import pandas as pd
import numpy as np
from parameters import WaterLPParameter
from datetime import datetime, timedelta


class New_Melones_Release_Policy(WaterLPParameter):

    def _value(self, timestep, scenario_index):
        multiplier = self.model.parameters['melones_storageValueConstant'].value(timestep, scenario_index)
        storage_value_numerator = self.model.parameters['melones_storage_value_numerator'].value(timestep, scenario_index)
        leading_multiplier = self.model.parameters['melones_storage_value_leading'].value(timestep, scenario_index)
        # return leading_multiplier * math.exp(multiplier * (storage_value_numerator / self.model.parameters["node/New Melones Reservoir/Elevation"].value(timestep, scenario_index)))
        return 1

    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)


New_Melones_Release_Policy.register()
print(" [*] New_Melones_Release_Policy successfully registered")
