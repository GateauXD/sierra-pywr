import pandas as pd


dataframe = pd.read_csv("Stan_Model/s3_imports/tot_runoff_sb1.csv")
for num in range(2,26):
    temp_dataframe = pd.read_csv("Stan_Model/s3_imports/tot_runoff_sb{}.csv".format(num))
    dataframe["flw"] = dataframe["flw"] + temp_dataframe["flw"]

dataframe.to_csv("Stan_Model/s3_imports/tot_runoff_sum.csv")
