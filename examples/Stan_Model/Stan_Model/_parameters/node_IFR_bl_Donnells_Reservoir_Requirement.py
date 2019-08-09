from parameters import WaterLPParameter

from utilities.converter import convert

class node_IFR_bl_Donnells_Reservoir_Requirement(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        
        WYT = get("WYI_SJValley")
        management = "BAU"
        path = "Management/{mgt}/IFRs/blDonnellsRes_daily.csv".format(mgt=management)
        data = self.read_csv(path, usecols=[0,1,2,3,4,5], index_col=0, header=None, names=['date','1','2','3','4','5'], parse_dates=False)
        if timestep.datetime.month >= 10:
        	dt = datetime.date(1999, timestep.datetime.month, timestep.datetime.day)
        else:
        	dt = datetime.date(2000, timestep.datetime.month, timestep.datetime.day)
        return data[str(WYT)][dt]
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_IFR_bl_Donnells_Reservoir_Requirement.register()
print(" [*] node_IFR_bl_Donnells_Reservoir_Requirement successfully registered")
