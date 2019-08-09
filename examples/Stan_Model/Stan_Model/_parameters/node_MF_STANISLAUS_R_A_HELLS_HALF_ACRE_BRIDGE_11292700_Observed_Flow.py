from parameters import WaterLPParameter

from utilities.converter import convert

class node_MF_STANISLAUS_R_A_HELLS_HALF_ACRE_BRIDGE_11292700_Observed_Flow(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        
        df = self.read_csv("Observed/Streamflow/GaugeStreamFlow_cms_STNR.csv", index_col=0, header=0)
        return df["11292700"][timestep.datetime]
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_MF_STANISLAUS_R_A_HELLS_HALF_ACRE_BRIDGE_11292700_Observed_Flow.register()
print(" [*] node_MF_STANISLAUS_R_A_HELLS_HALF_ACRE_BRIDGE_11292700_Observed_Flow successfully registered")
