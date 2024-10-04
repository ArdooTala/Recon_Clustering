import importlib.util
import logging
import networkx as nx
import matplotlib.pyplot as plt
import warnings


logger = logging.getLogger(__name__)

VIZ_DEP_INSTALLED = (importlib.util.find_spec('pygraphviz')) is not None

def viz_g(g):
    subax1 = plt.subplot()
    pos = nx.spring_layout(g)
    nx.draw_networkx(g, pos=pos, with_labels=True)
    plt.show()

def viz_dag(g, pos):
    subax1 = plt.subplot()
    nx.draw_networkx(g, pos=pos, with_labels=True)
    plt.show()

def pygraphviz_layout(g):
    if not VIZ_DEP_INSTALLED:
        warnings.warn("Package pygraphviz is not installed. Skipping visualization.")
        return
    gg = nx.nx_agraph.to_agraph(g)
    gg.layout(
        prog="dot",
        args="-Grankdir='TB' -Granksep=0.5 -Gsplines='false' -Gnodesep=0.02 -Goutputorder='edgesfirst'"
    )
    bbox = tuple(map(float, gg.graph_attr['bb'].split(',')))
    # bbox = gg.graph_attr['bb'].split(',')
    pos = {}
    for node in gg.nodes():
        pos[node] = tuple(map(float, gg.get_node(node).attr["pos"].split(',')))

    logger.debug(f"Node Positions: {pos}")
    return pos, bbox

def multipartite_layout_by_connections(g):
    graph = nx.subgraph_view(
        g,
        filter_edge=lambda e1, e2: g[e1][e2].get("EDGE_TYPE", None) != "COLL",
    ).copy()

    stage = 0
    while graph.order() > 0:
        sources = [x for x, ind in graph.in_degree if ind == 0]
        if not sources:
            raise Exception("FUCK!...No Sources in Graph")
        for src in sources:
            g.nodes[src]['subset'] = stage
        graph.remove_nodes_from(sources)

        stage += 1
    pos = nx.multipartite_layout(g)
    logger.debug(f"Node Positions: {pos}")
    return pos, (0, 0, 1, 1)
