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


def trim_connection_graph(nodes):
    elems = set()
    for no in nodes:
        el = list(con.predecessors(no))
        elems.update(el)
    sub_ass = con.subgraph(list(elems) + list(nodes))

    nx.draw(sub_ass, with_labels=True, font_weight='bold')
    plt.show()

    sub_ass_parts = list(nx.weakly_connected_components(sub_ass))
    print(sub_ass_parts)

    for part in sub_ass_parts:
        sd = dep.subgraph(part)
        yield sd


def collapse_nodes(ass):
    con_dep = get_con_dep_graph_from_dep(ass)
    nx.draw(con_dep, with_labels=True, font_weight='bold')
    plt.show()

    if nx.is_directed_acyclic_graph(con_dep):
        return con_dep

    scc = list(max(nx.strongly_connected_components(con_dep), key=len))
    print(scc)

    subG = ass.subgraph(scc)
    nx.draw(subG, with_labels=True, font_weight='bold')
    plt.show()

    return

    cond_ass_cp = cond_ass.copy()
    for n in cond_ass_cp.nodes:
        subG = ass.subgraph(cond_ass_cp.nodes[n]['members'])

        print(f"Cluster with {subG.order()} Connections")
        for sub_dep in trim_connection_graph(subG):
            nx.draw(sub_dep, with_labels=True, font_weight='bold')
            plt.show()

            print(f"Sorting SubDep {sub_dep}")

            topo_sort_ass(sub_dep, stage + 1, step)

        cond_ass.remove_node(n)

    new_graph = con_dep.copy()
    for node in scc[1:]:
        print(node)
        new_graph = nx.contracted_nodes(new_graph, scc[0], node, self_loops=False)
        nx.draw(new_graph, with_labels=True, font_weight='bold')
        plt.show()

    nx.draw(new_graph, with_labels=True, font_weight='bold')
    plt.show()


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
                for sub_dep in trim_connection_graph(subG):
                    nx.draw(sub_dep, with_labels=True, font_weight='bold')
                    plt.show()

                    print(f"Sorting SubDep {sub_dep}")

                    topo_sort_ass(sub_dep, stage + 1, step)

            cond_ass.remove_node(n)

        print(f"{cond_ass} remaining")
        step += 1


topo_sort_ass(dep)
# collapse_nodes(dep)
