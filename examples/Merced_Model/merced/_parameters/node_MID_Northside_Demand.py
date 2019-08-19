import pandas as pd
from parameters import WaterLPParameter

from utilities.converter import convert

yearly_types = pd.read_csv("s3_imports/SJVI.csv", index_col=0, header=0, parse_dates=False,
                           squeeze=True)


class node_MID_Northside_Demand(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        m3_to_cfs = 35.31
        type_value = yearly_types.loc[timestep.year]
        ts = "{}/{}/1900".format(timestep.month, timestep.day)

        if type_value <= 2.1:
            year_type = "Critical"
        elif type_value <= 2.8:
            year_type = "Dry"
        elif type_value <= 3.1:
            year_type = "Below"
        elif type_value <= 3.8:
            year_type = "Above"
        else:
            year_type = "Wet"

        return pd.read_csv("policies/MID_WYT_average_diversion_Main.csv", index_col=0, header=0, squeeze=True).loc[
                   ts, year_type] / m3_to_cfs
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_MID_Northside_Demand.register()
print(" [*] node_MID_Northside_Demand successfully registered")
