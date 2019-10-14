import datetime
from parameters import WaterLPParameter

from utilities.converter import convert


class node_IFR_bl_New_Spicer_Meadow_Reservoir_Cost(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        return 0

    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)


node_IFR_bl_New_Spicer_Meadow_Reservoir_Cost.register()
print(" [*] node_IFR_bl_New_Spicer_Meadow_Reservoir_Cost successfully registered")
