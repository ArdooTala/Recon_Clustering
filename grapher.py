import networkx as nx
import matplotlib.pyplot as plt
from example_graph import con, dep


subax1 = plt.subplot()
nx.draw(dep, with_labels=True, font_weight='bold')
plt.show()


def get_con_dep_graph_from_dep(dep_graph):
    con_dep = dep_graph.copy()
    for n, is_part in dep_graph.nodes.data("PART"):
        if not is_part:
            continue
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

    print(f"Trimmed Graph w/ Nodes {nodes}")
    nx.draw(sub_ass, with_labels=True, font_weight='bold')
    plt.show()

    return sub_ass


def collapse_nodes(ass):
    con_dep = get_con_dep_graph_from_dep(ass)
    nx.draw(con_dep, with_labels=True, font_weight='bold')
    plt.show()

    new_graph = con_dep.copy()
    while not nx.is_directed_acyclic_graph(new_graph):
        scc = list(max(nx.strongly_connected_components(new_graph), key=len))
        print(f"Found a SCC -> {scc}")

        trm_dep_graph = get_dep_graph_from_connections(ass, scc)
        trm_dep_con = get_con_dep_graph_from_dep(trm_dep_graph)
        nx.draw(trm_dep_con, with_labels=True, font_weight='bold')
        plt.show()

        trm_con_graph = get_dep_graph_from_connections(con, scc)
        clusters = list(nx.weakly_connected_components(trm_con_graph))
        print(f"Main Clusters: {clusters}")
        segmented_dep_graph = nx.union_all([ass.subgraph(cluster) for cluster in clusters])
        trm_con_con = get_con_dep_graph_from_dep(segmented_dep_graph)
        nx.draw(trm_con_con, with_labels=True, font_weight='bold')
        plt.show()

        nx.draw(new_graph, with_labels=True, font_weight='bold')
        plt.show()
        for edge in trm_dep_con.edges:
            if not trm_con_con.has_edge(*edge):
                print(f"Removing dep Edge: {edge}")
                new_graph.remove_edge(*edge)
        nx.draw(new_graph, with_labels=True, font_weight='bold')
        plt.show()

        for sub_dep in nx.weakly_connected_components(trm_con_graph):
            print(sub_dep)
            clstr_nodes = [n for n in sub_dep if new_graph.has_node(n)]
            print(clstr_nodes)

            cluster_node = ";".join(clstr_nodes)
            new_graph.add_node(cluster_node)
            for node in clstr_nodes:
                print(f"NODE: {node}")
                new_graph = nx.contracted_nodes(new_graph, cluster_node, node, self_loops=False)
            nx.draw(new_graph, with_labels=True, font_weight='bold')
            plt.show()

        nx.draw(new_graph, with_labels=True, font_weight='bold')
        plt.show()

    return new_graph


def topo_sort_ass(ass, stage=0, step=0):
    con_dep = get_con_dep_graph_from_dep(ass)
    nx.draw(con_dep, with_labels=True, font_weight='bold')
    plt.show()

    cond_ass = nx.condensation(con_dep)
    nx.draw(cond_ass, with_labels=True, font_weight='bold')
    plt.show()

    while cond_ass.order() > 0:
        print(f"STEP #{step}")
        cond_ass_cp = cond_ass.copy()
        for n in cond_ass_cp.nodes:
            if cond_ass_cp.out_degree(n) > 0:
                continue

            subG = cond_ass_cp.nodes[n]['members']
            if len(subG) == 1:
                print(f"\t>>> {subG} {stage}:{step}")
            else:
                print(f"Cluster with {len(subG)} Connections")
                for sub_dep in nx.weakly_connected_components(get_dep_graph_from_connections(subG)):
                    nx.draw(sub_dep, with_labels=True, font_weight='bold')
                    plt.show()

                    print(f"Sorting SubDep {sub_dep}")

                    topo_sort_ass(sub_dep, stage + 1, step)

            cond_ass.remove_node(n)

        print(f"{cond_ass} remaining")
        step += 1


final_con = collapse_nodes(dep)

nx.draw(final_con, with_labels=True, font_weight='bold')
plt.show()
