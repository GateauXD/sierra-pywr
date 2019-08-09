import os
from graphviz import Digraph
import json

os.environ["PATH"] += os.pathsep + 'C:/Program Files (x86)/Graphviz2.38/bin/'

with open("Merced_Model/merced/pywr_model.json") as f:
    model = json.load(f)

dot = Digraph(comment='System')
dot.edges(model['edges'])
dot.render('Merced_Model/system.gv', view=True)