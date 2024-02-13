import networkx as nx
import matplotlib.pyplot as plt
import pygraphviz as pgv
# from example_graph import con, dep
from main import con, dep


def viz_g(g):
    nx.draw_circular(g, with_labels=True, font_weight='bold')
    plt.show()


def get_con_dep_graph_from_dep(dep_graph):
    con_dep = dep_graph.copy()
    print("#" * 100)
    for n, t in dep_graph.nodes.data("TYPE"):
        if t != "PART":
            print(f"{n} is NOT Part: {dep_graph.nodes[n]}")
            continue
        print(f"{n} is Part")
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


def collapse_nodes(graph, nodes, cluster_node, save_dict=None, node_type=""):
    subg = graph.subgraph(nodes)
    cluster_level_data = subg.nodes.data('level', default=-1)
    cluster_level = max([lvl for _, lvl in cluster_level_data]) + 1
    print(f"\t >> CLUSTER LEVEL IS > {cluster_level}")

    # cluster_node = f"C[{';'.join([str(c) for c in nodes])}]"
    graph.add_node(cluster_node, TYPE="PART", level=cluster_level)
    for node in nodes:
        print(f"Contracting NODE {cluster_node} and {node}")
        graph = nx.contracted_nodes(graph, cluster_node, node, self_loops=False)
    # viz_g(graph)

    if save_dict is not None:
        clst_list = save_dict.get(cluster_level, [])
        clst_list.append(
            (
                cluster_node,
                [str(c) for c in nodes if subg.nodes[c].get("TYPE", None) == node_type]
            )
        )
        save_dict[cluster_level] = clst_list

    return graph


def process_graph(ass_dep, ass_con):
    con_dep = get_con_dep_graph_from_dep(ass_dep)
    viz_g(con_dep)

    new_ass_con = ass_con.copy()
    new_ass_dep = ass_dep.copy()
    new_con_dep = con_dep.copy()

    cluster_num = 0
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
            # viz_g(seg_con_dep)

            # Remove edges from ConnectionsDependencyGraph
            # viz_g(new_con_dep)
            for edge in trm_con_dep.edges:
                if not seg_con_dep.has_edge(*edge):
                    print(f"Removing dep Edge: {edge}")
                    new_con_dep.remove_edge(*edge)
            # viz_g(new_con_dep)

            for cluster in clusters:
                cluster_name = f"CL_{cluster_num:02}"
                cluster_num += 1

                clstr_nodes = [n for n in cluster if new_con_dep.has_node(n)]
                print(f"{cluster_name} > {cluster} > CON Nodes > {clstr_nodes}")

                # Update ConnectionsDependencyGraph
                new_con_dep = collapse_nodes(
                    new_con_dep, clstr_nodes, cluster_name, save_dict=clusters_dict_conns, node_type="CONN"
                )

                # Update AssemblyConnectionsGraph
                new_ass_con = collapse_nodes(
                    new_ass_con, cluster, cluster_name, save_dict=clusters_dict_parts, node_type="PART"
                )

                # Update AssemblyDependencyGraph
                new_ass_dep = collapse_nodes(new_ass_dep, cluster, cluster_name)

            export_graph(new_con_dep, "con_dep")
            export_graph(new_ass_con, "ass_con")
            export_graph(new_ass_dep, "ass_dep")

    return new_con_dep


def export_graph(g, name):
    nx.nx_agraph.to_agraph(g).draw(f"exports/{name}.pdf", prog="dot")


subax1 = plt.subplot()
export_graph(dep, "dep")

clusters_dict_parts = {}
clusters_dict_conns = {}
final_con = process_graph(dep, con)
print("FIN")
export_graph(final_con, "res")

layer = 0
layers_dict = {}
clusters = []
while final_con.order() > 0:
    print(final_con)
    # find sources
    sources = [x for x in final_con.nodes() if final_con.in_degree(x) == 0]
    print(sources)
    layers_dict[layer] = sources
    final_con.remove_nodes_from(sources)

    layer += 1

print(clusters_dict_parts)
print(clusters_dict_conns)
print(layers_dict)

with open("exports/export-layers.csv", 'w') as file:
    for lay in layers_dict.items():
        file.write(f"LAYER{lay[0]},{';'.join(lay[1])}\n")

with open("exports/export-clusters-parts.csv", 'w') as file:
    for lay in clusters_dict_parts.items():
        for clst in lay[1]:
            file.write(f"LAYER{lay[0]},{clst[0]},{';'.join(clst[1])}\n")

with open("exports/export-clusters-conns.csv", 'w') as file:
    for lay in clusters_dict_parts.items():
        for clst in lay[1]:
            file.write(f"LAYER{lay[0]},{clst[0]},{';'.join(clst[1])}\n")
