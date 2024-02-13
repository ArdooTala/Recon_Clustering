import networkx as nx
import matplotlib.pyplot as plt
import pygraphviz as pgv
from example_graph import con, dep


def viz_g(g):
    nx.draw_circular(g, with_labels=True, font_weight='bold')
    plt.show()


def get_con_dep_graph_from_dep(dep_graph):
    con_dep = dep_graph.copy()
    print("#"*100)
    for n, is_part in dep_graph.nodes.data("PART"):
        if not is_part:
            print(f"{n} is NOT Part: {dep_graph.nodes[n]}")
            continue
        print(f"{n} is PART")
        for s in con_dep.successors(n):
            for p in list(con_dep.predecessors(n)):
                con_dep.add_edge(p, s)

        con_dep.remove_node(n)

    return con_dep


def get_dep_graph_from_connections(graph, nodes):
    elems = set()
    for no in nodes:
        el = list(graph.predecessors(no))
        elems.update(el)
    sub_ass = graph.subgraph(list(elems) + list(nodes)).copy()

    return sub_ass


def collapse_nodes(graph, nodes):
    # graph = graph.copy()
    cluster_node = f"C[{';'.join([str(c) for c in nodes])}]"
    graph.add_node(cluster_node, PART=True)
    for node in nodes:
        print(f"Contracting NODE {cluster_node} and {node}")
        graph = nx.contracted_nodes(graph, cluster_node, node, self_loops=False)
    viz_g(graph)

    return graph


def process_graph(ass_dep, ass_con):
    con_dep = get_con_dep_graph_from_dep(ass_dep)
    viz_g(con_dep)

    new_ass_con = ass_con.copy()
    new_ass_dep = ass_dep.copy()
    new_con_dep = con_dep.copy()
    while not nx.is_directed_acyclic_graph(new_con_dep):
        condensed = nx.condensation(new_con_dep)
        for scc_node in list(nx.topological_sort(condensed)):
            scc = condensed.nodes[scc_node]['members']
            print(f"SCC >> {scc}")
            if len(scc) < 2:
                continue
            print(f"Found a SCC -> {scc}")

            trm_con_dep = new_con_dep.subgraph(scc).copy()
            viz_g(trm_con_dep)

            trm_ass_con = get_dep_graph_from_connections(new_ass_con, scc)
            clusters = list(nx.weakly_connected_components(trm_ass_con))
            print(f"Main Clusters: {clusters}")
            seg_ass_dep = nx.union_all([new_ass_dep.subgraph(cluster) for cluster in clusters])
            seg_con_dep = get_con_dep_graph_from_dep(seg_ass_dep)
            viz_g(seg_con_dep)

            # Remove edges from ConnectionsDependencyGraph
            viz_g(new_con_dep)
            for edge in trm_con_dep.edges:
                if not seg_con_dep.has_edge(*edge):
                    print(f"Removing dep Edge: {edge}")
                    new_con_dep.remove_edge(*edge)
            viz_g(new_con_dep)

            for cluster in clusters:
                clstr_nodes = [n for n in cluster if new_con_dep.has_node(n)]
                print(f"{cluster} > CON Nodes > {clstr_nodes}")

                # Update ConnectionsDependencyGraph
                new_con_dep = collapse_nodes(new_con_dep, clstr_nodes)

                # Update AssemblyConnectionsGraph
                new_ass_con = collapse_nodes(new_ass_con, cluster)

                # Update AssemblyDependencyGraph
                new_ass_dep = collapse_nodes(new_ass_dep, cluster)

            export_graph(new_con_dep, "con_dep")
            export_graph(new_ass_con, "ass_con")

    return new_con_dep


def export_graph(g, name):
    nx.nx_agraph.to_agraph(g).draw(f"exports/{name}.pdf", prog="dot")


subax1 = plt.subplot()
export_graph(dep, "dep")

final_con = process_graph(dep, con)
print("FIN")
export_graph(final_con, "res")
