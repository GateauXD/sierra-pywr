import matplotlib.pyplot as plt
import pandas as pd
from pylab import rcParams

def generate_csv():
    results_csv = pd.read_csv("merced/results.csv", skiprows=[1])
    results_csv = results_csv[['Recorder', 'node/Lake McClure/storage']].copy()
    return results_csv


def main():
    graph_data = generate_csv()

    rcParams['figure.figsize'] = 24, 12
    fig = plt.figure()
    ax = plt.gca()

    fig.add_subplot(graph_data.plot(kind='line', x='Recorder', y='node/Lake McClure/storage', ax=ax))
    plt.show()

if __name__ == "__main__":
    main()