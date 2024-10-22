import networkx as nx
import textwrap as tw
import pygraphviz as pgv
import matplotlib.pyplot as plt

from recongraph.io_utils import graph_generator


def to_dot(graph, clustered_graph):
    return f"digraph {graph.name} {{\n"\
           f"{tw.indent(_write_nodes(clustered_graph), '\t')}"\
           f"\n\n"\
           f"{tw.indent(_write_edges(graph), '\t')}"\
           f"\n}}"


def _write_edges(graph):
    edges = map(_write_edge, graph.edges)
    return f"{f'\n'.join(edges)}"


def _write_nodes(nodes):
    nodes = map(_write_node, nodes)
    return f"{f'\n'.join(nodes)}"


def _write_edge(edge, color='black'):
    return f"{edge[0]} -> {edge[1]} [color={color}]"


def _write_node(node, color='black', shape='circle'):
    if isinstance(node, nx.Graph):
        return f"subgraph cluster_{node.name} {{\n{tw.indent(_write_nodes(node), '\t')}\n}}"

    return f"{node} [color={color}]"


if __name__ == "__main__":
    assembly = graph_generator.graph_from_dot_file("../assemblies/simple.dot")
    clusters = {
        'cls_1': [
            'b',
            'c',
            'd',
            'bc',
            'bd',
        ],
        'cls_2': [
            'e',
            'f',
            'g',
            'ef',
            'eg',
        ]
    }
    clustered_assembly = assembly.copy()
    for cluster in clusters:
        subg = clustered_assembly.subgraph(clusters[cluster]).copy()
        subg.name = cluster
        clustered_assembly.add_node(subg)
        for node in subg.nodes:
            nx.contracted_nodes(clustered_assembly, subg, node, copy=False)
    dot = to_dot(assembly, clustered_assembly)
    print(dot)
    with open("KIR.dot", 'w') as f:
        f.write(dot)