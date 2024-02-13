import networkx as nx
import matplotlib.pyplot as plt
from example_graph import con, dep


subax1 = plt.subplot()


def viz_g(g):
    nx.draw_circular(g, with_labels=True, font_weight='bold')
    plt.show()


viz_g(dep)


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
    sub_ass = graph.subgraph(list(elems) + list(nodes))

    return sub_ass


def collapse_nodes(ass_dep, ass):
    con_dep = get_con_dep_graph_from_dep(ass_dep)
    viz_g(con_dep)

    new_ass = ass.copy()
    new_ass_dep = ass_dep.copy()
    new_graph = con_dep.copy()
    while not nx.is_directed_acyclic_graph(new_graph):
        condensed = nx.condensation(new_graph)
        for scc_node in list(nx.topological_sort(condensed)):
            scc = condensed.nodes[scc_node]['members']
            print(f"SCC >> {scc}")
            if len(scc) < 2:
                continue
            print(f"Found a SCC -> {scc}")

            trm_dep_con = con_dep.subgraph(scc)
            viz_g(trm_dep_con)

            trm_con_graph = get_dep_graph_from_connections(new_ass, scc)
            clusters = list(nx.weakly_connected_components(trm_con_graph))
            print(f"Main Clusters: {clusters}")
            segmented_dep_graph = nx.union_all([new_ass_dep.subgraph(cluster) for cluster in clusters])
            trm_con_con = get_con_dep_graph_from_dep(segmented_dep_graph)
            viz_g(trm_con_con)

            viz_g(new_graph)
            for edge in trm_dep_con.edges:
                if not trm_con_con.has_edge(*edge):
                    print(f"Removing dep Edge: {edge}")
                    new_graph.remove_edge(*edge)
            viz_g(new_graph)

            for cluster in clusters:
                clstr_nodes = [n for n in cluster if new_graph.has_node(n)]
                print(f"{cluster} > CON Nodes > {clstr_nodes}")

                cluster_node = f"C[{';'.join(clstr_nodes)}]"
                new_graph.add_node(cluster_node, PART=True)
                for node in clstr_nodes:
                    print(f"Contracting NODE {cluster_node} and {node}")
                    new_graph = nx.contracted_nodes(new_graph, cluster_node, node, self_loops=False)
                viz_g(new_graph)

                ass_cluster_node = f"AC[{';'.join([str(c) for c in cluster])}]"
                new_ass.add_node(ass_cluster_node, PART=True)
                for node in cluster:
                    print(f"Contracting NODE {ass_cluster_node} and {node}")
                    new_ass = nx.contracted_nodes(new_ass, ass_cluster_node, node, self_loops=False)
                viz_g(new_ass)

                ass_cluster_node = f"AC[{';'.join([str(c) for c in cluster])}]"
                new_ass_dep.add_node(ass_cluster_node, PART=True)
                for node in cluster:
                    print(f"Contracting NODE {ass_cluster_node} and {node}")
                    new_ass_dep = nx.contracted_nodes(new_ass_dep, ass_cluster_node, node, self_loops=False)
                viz_g(new_ass_dep)

            viz_g(new_graph)
            viz_g(new_ass)

    return new_graph


final_con = collapse_nodes(dep, con)
print("FIN")
viz_g(final_con)
