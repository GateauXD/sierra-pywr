from parameters import WaterLPParameter

from utilities.converter import convert

class node_BEAVER_C_DIV_TO_MCKAYS_POINT_RES_NR_ARNO_11295210_Observed_Flow(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        
        df = self.read_csv("Observed/Streamflow/GaugeStreamFlow_cms_STNR.csv", index_col=0, header=0)
        return df["11295210"][timestep.datetime]
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_BEAVER_C_DIV_TO_MCKAYS_POINT_RES_NR_ARNO_11295210_Observed_Flow.register()
print(" [*] node_BEAVER_C_DIV_TO_MCKAYS_POINT_RES_NR_ARNO_11295210_Observed_Flow successfully registered")
