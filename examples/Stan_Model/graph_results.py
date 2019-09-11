import matplotlib.pyplot as plt
import pandas as pd
from pylab import rcParams

recorder = ["Recorder"]
items_of_interest = ["node/Beardsley Reservoir/storage", "node/Donnells Reservoir/storage", "node/Lyons Reservoir/storage",
                     "node/New Spicer Meadow Reservoir/storage", "node/Pinecrest Reservoir/storage", "node/Relief Reservoir/storage"]
observed_items = []

for item in items_of_interest:
    split_item = item.split("/")
    split_item[-1] = "observed " + split_item[-1]
    observed_items.append("/".join(split_item))

def generate_csv():
    results_csv = pd.read_csv("Stan_Model/results.csv", skiprows=[1])
    results_csv = results_csv[recorder + items_of_interest + observed_items].copy()

    return results_csv


def main():
    graph_data = generate_csv()

    rcParams['figure.figsize'] = 24, 12
    for index, item in enumerate(items_of_interest):
        fig = plt.figure()
        ax = plt.gca()
        fig.add_subplot(graph_data.plot(kind='line', x='Recorder', y=item, ax=ax))
        fig.add_subplot(graph_data.plot(kind='line', x='Recorder', y=observed_items[index], ax=ax))
        fig.savefig("Figures/{}.png".format(item.split("/")[1]), dpi=100)

if __name__ == "__main__":
    main()