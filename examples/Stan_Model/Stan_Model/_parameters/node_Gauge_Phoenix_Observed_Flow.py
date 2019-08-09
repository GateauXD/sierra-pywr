from parameters import WaterLPParameter

from utilities.converter import convert

class node_Gauge_Phoenix_Observed_Flow(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        kwargs = dict(timestep=timestep, scenario_index=scenario_index)
        path="{ExternalDir}/GAGES/Gauge_Phoenix.csv".format(ExternalDir=self.GET("network/1224/1594", **kwargs))
        data = self.read_csv(path, usecols=[0,1,2], comment=';', header=None, **kwargs)
        return data.iloc[timestep][2]*self.GET("network/1224/1584", **kwargs)
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_Gauge_Phoenix_Observed_Flow.register()
print(" [*] node_Gauge_Phoenix_Observed_Flow successfully registered")
