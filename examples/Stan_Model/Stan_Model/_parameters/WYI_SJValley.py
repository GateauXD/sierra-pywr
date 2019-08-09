from parameters import WaterLPParameter

from utilities.converter import convert

class WYI_SJValley(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        
        return Scenarios/Livneh/WYT/SJVI.csv
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "ac-ft", "m^3", scale_in=1000000, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
WYI_SJValley.register()
print(" [*] WYI_SJValley successfully registered")
