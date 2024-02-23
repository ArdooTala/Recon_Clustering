import networkx as nx
import matplotlib.pyplot as plt


def viz_g(g):
    subax1 = plt.subplot()
    nx.draw_circular(g, with_labels=True, font_weight='bold')
    plt.show()
