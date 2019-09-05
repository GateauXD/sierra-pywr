import math
import pandas as pd
import numpy as np
from parameters import WaterLPParameter
from datetime import datetime, timedelta


class one_storage_value (WaterLPParameter):

    def _value(self, timestep, scenario_index):
        storage_value = self.model.parameters['storage_value_for_all'].value(timestep, scenario_index)

        return storage_value

    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)


one_storage_value.register()
print(" [*] one_storage_value successfully registered")
