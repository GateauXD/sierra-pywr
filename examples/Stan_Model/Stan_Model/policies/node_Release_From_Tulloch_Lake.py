import math
import pandas as pd
import numpy as np
from utilities import get_year_type
from parameters import WaterLPParameter
from datetime import datetime, timedelta


class node_Release_From_Tulloch_Lake(WaterLPParameter):

    def get_demand(self, timestep, scenario_index):

        year_names = ["Critical", "Dry", "Below", "Above", "Wet"]
        year_type = year_names[get_year_type-1]



        net_demand_csv = pd.read_csv("s3_imports/NetDemand_belowTulloch.csv", index_col=[0])
        net_demand_csv.index = pd.to_datetime(net_demand_csv.index)


    def _value(self, timestep, scenario_index):
        out_flow = self.model.nodes["Tulloch Lake [node]"].volume[-1] + self.model.nodes["STN_below_Melons.2.2"].flow[-1] - self.model.parameters["node/Tulloch Lake/Storage Demand"].value(timestep, scenario_index)
        net_demand = self.get_demand(timestep, scenario_index) + self.model.parameters["node/blwTullochPH/Requirement"].value(timestep, scenario_index)
        return max(net_demand, min(out_flow, 226.535))

    def value(self, timestep, scenario_index):
        return self._value(timestep, scenario_index)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)


node_Release_From_Tulloch_Lake.register()
print(" [*] node_Release_From_Tulloch_Lake successfully registered")
