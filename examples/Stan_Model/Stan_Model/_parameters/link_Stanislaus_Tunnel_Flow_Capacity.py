from parameters import WaterLPParameter

from utilities.converter import convert

class link_Stanislaus_Tunnel_Flow_Capacity(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        kwargs = dict(timestep=timestep, scenario_index=scenario_index)
        return 530*self.GET("network/1224/1584", **kwargs)
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
link_Stanislaus_Tunnel_Flow_Capacity.register()
print(" [*] link_Stanislaus_Tunnel_Flow_Capacity successfully registered")
