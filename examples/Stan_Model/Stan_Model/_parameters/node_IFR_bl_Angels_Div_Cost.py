qimport
datetime
from parameters import WaterLPParameter
from utilities.converter import convert
from utilities.get_year_type import getSJVI_WYT

class node_IFR_bl_Angels_Div_Cost(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        return 1


    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)


node_IFR_bl_Angels_Div_Cost.register()
print(" [*] node_IFR_bl_Angels_Div_Cost successfully registered")
