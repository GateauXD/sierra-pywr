import os
from graphviz import Digraph
import json

os.environ["PATH"] += os.pathsep + 'C:/Program Files (x86)/Graphviz2.38/bin/'

with open("Stan_Model/pywr_model.json") as f:
    model = json.load(f)

dot = Digraph(comment='System')
dot.edges(model['edges'])
dot.render('Stan_Model/system.gv', view=True)