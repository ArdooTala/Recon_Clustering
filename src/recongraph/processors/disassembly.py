import networkx as nx
import logging

from networkx.classes import subgraph_view

logger = logging.getLogger(__name__)


def find_connection_nodes_to_remove(assembly: nx.DiGraph, part):
    ass_graph = nx.subgraph_view(
        assembly,
        filter_edge=lambda e1, e2: assembly[e1][e2]["EDGE_TYPE"] != "COLL",
    ).copy()

    break_points = [conn for conn in ass_graph.successors(part) if ass_graph.nodes.data("TYPE")[conn] == "CONN"]
    print(break_points)

    parts_to_include = [part, ] + break_points
    subgraph_to_remove = assembly.subgraph(parts_to_include)
    print(assembly)
    print(subgraph_to_remove)
    print(nx.is_directed_acyclic_graph(subgraph_to_remove))

    for bp in break_points:
        collisions = [n for n in assembly.adj[bp] if assembly[bp][n]['EDGE_TYPE'] == 'COLL']
        if not collisions:
            continue
        print(bp, collisions)
        parts_to_include += [pred for pred in ass_graph.predecessors(bp) if pred not in parts_to_include]
        print(parts_to_include)
