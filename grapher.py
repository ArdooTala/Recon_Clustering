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


def trim_connection_graph(sub_graph):
    elems = set()
    for no in sub_graph.nodes:
        el = list(con.predecessors(no))
        elems.update(el)
    sub_ass = con.subgraph(list(elems) + list(sub_graph.nodes))

    nx.draw(sub_ass, with_labels=True, font_weight='bold')
    plt.show()

    sub_ass_parts = list(nx.weakly_connected_components(sub_ass))
    print(sub_ass_parts)

    for part in sub_ass_parts:
        sd = dep.subgraph(part)
        yield sd


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

            subG = ass.subgraph(cond_ass_cp.nodes[n]['members'])
            if subG.order() == 1:
                print(f"\t>>> {subG.nodes} {stage}:{step}")
            else:
                print(f"Cluster with {subG.order()} Connections")
                for sub_dep in trim_connection_graph(subG):
                    nx.draw(sub_dep, with_labels=True, font_weight='bold')
                    plt.show()

                    print(f"Sorting SubDep {sub_dep}")

                    topo_sort_ass(sub_dep, stage + 1, step)

            cond_ass.remove_node(n)

        print(f"{cond_ass} remaining")
        step += 1


topo_sort_ass(dep)
