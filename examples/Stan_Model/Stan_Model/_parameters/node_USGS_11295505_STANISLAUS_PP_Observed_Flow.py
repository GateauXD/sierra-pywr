from parameters import WaterLPParameter

from utilities.converter import convert

class node_USGS_11295505_STANISLAUS_PP_Observed_Flow(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        
        df = self.read_csv("Observed/Streamflow/GaugeStreamFlow_cms_STNR.csv", index_col=0, header=0)
        return df["11295505"][timestep.datetime]
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_USGS_11295505_STANISLAUS_PP_Observed_Flow.register()
print(" [*] node_USGS_11295505_STANISLAUS_PP_Observed_Flow successfully registered")
