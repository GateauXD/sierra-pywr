from parameters import WaterLPParameter

from utilities.converter import convert

class node_Lake_McClure_Storage_Demand(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        return self.model.parameters["node/Lake McClure/Storage Capacity"].value(timestep, scenario_index)  # Units Million M^3
        
    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_Lake_McClure_Storage_Demand.register()
print(" [*] node_Lake_McClure_Storage_Demand successfully registered")
