from parameters import WaterLPParameter

from utilities.converter import convert

class node_New_Melones_Lake_Observed_Storage(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        
        df = self.read_csv("Observed/Reservoirs/GaugeReservoir_mcm_STNR.csv", index_col=0, header=0)
        return df["New Melones Lake"][timestep.datetime]
        
    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_New_Melones_Lake_Observed_Storage.register()
print(" [*] node_New_Melones_Lake_Observed_Storage successfully registered")
