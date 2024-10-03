import networkx as nx
import matplotlib.pyplot as plt


def viz_g(g):
    subax1 = plt.subplot()
    pos = nx.spectral_layout(g)
    nx.draw_networkx(g, pos=pos, with_labels=True, font_weight='bold')
    plt.show()

def viz_dag(g):
    gg = g.copy()
    dg = nx.subgraph_view(
        g,
        filter_edge=lambda e1, e2: g[e1][e2].get("EDGE_TYPE", None) != "COLL",
    )
    graph = dg.copy()
    stage = 0
    while graph.order() > 0:
        print(graph)

        sources = [x for x, ind in graph.in_degree if ind == 0]
        print(f"Source Nodes: {sources}")
        if not sources:
            raise Exception("FUCK!...No Sources in Graph")
        for src in sources:
            gg.nodes[src]['subset'] = stage
        graph.remove_nodes_from(sources)

        stage += 1

    subax1 = plt.subplot()
    pos = nx.multipartite_layout(gg)
    nx.draw_networkx(gg, pos=pos, with_labels=True, font_weight='bold')
    plt.show()
