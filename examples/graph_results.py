import matplotlib.pyplot as plt
import pandas as pd
from pylab import rcParams

def generate_csv():
    wyt_values = {1980:1,1981:2,1982:1,1983:1,1984:1,1985:2,1986:1,1987:2,1988:2,1989:2,1990:2,1991:1,1992:2,1993:1,1994:2,1995:1,
                1996:1,1997:1,1998:1,1999:1,2000:1,2001:2,2002:2,2003:1,2004:2,2005:1,2006:1,2007:2,2008:2,
                2009:1,2010:1,2011:1,2012:2,2013:2,}
    results_csv = pd.read_csv("merced/results.csv", skiprows=[1])
    results_csv = results_csv[['Recorder', 'node/Lake McClure/observed storage', 'node/Lake McClure/storage']].copy()
    wyt_series = []

    for index, row in results_csv.iterrows():
        wyt_series.append(wyt_values[int(row['Recorder'].split("-")[0])])

    results_csv["WTS_Value"] = wyt_series

    return results_csv


def main():
    graph_data = generate_csv()

    # Set dimensions for resulting image in pixes (width x height)
    rcParams['figure.figsize'] = 30, 15

    # Graph the storage results
    fig, ax1 = plt.subplots()
    ax1.plot(graph_data["node/Lake McClure/observed storage"], label="Observed Storage")
    ax1.plot(graph_data["node/Lake McClure/storage"], label="Storage")
    ax1.legend()
    # Setup secondary axis
    ax2 = ax1.twinx()
    ax2.plot(graph_data["WTS_Value"], 'g', label="WTS")
    plt.show()
    fig.savefig("result_graph.png", dpi=100)

if __name__ == "__main__":
    main()
