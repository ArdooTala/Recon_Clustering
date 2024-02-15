import networkx as nx
import matplotlib.pyplot as plt
import pygraphviz as pgv
# from example_graph import con, dep
from main import con, dep


def viz_g(g):
    nx.draw_circular(g, with_labels=True, font_weight='bold')
    plt.show()


def get_con_dep_graph_from_dep(dep_graph, drop_types=None):
    if not drop_types:
        drop_types = ["PART"]

    con_dep = dep_graph.copy()
    # print("#" * 100)
    for n, t in dep_graph.nodes.data("TYPE"):
        if t not in drop_types:
            continue

        for s in con_dep.successors(n):
            for p in list(con_dep.predecessors(n)):
                if s == p:
                    continue
                con_dep.add_edge(p, s)

        con_dep.remove_node(n)

    return con_dep


def get_dep_graph_from_connections(graph, nodes):
    elems = set()
    for no in nodes:
        el = list(graph.predecessors(no))
        elems.update(el)
    return graph.subgraph(list(elems) + list(nodes)).copy()


def collapse_nodes(graph, nodes, cluster_node, save_dict=None):
    subg = graph.subgraph(nodes).copy()
    cluster_level_data = subg.nodes.data('level', default=-1)
    cluster_level = max([lvl for _, lvl in cluster_level_data]) + 1
    print(f"\t >> {cluster_node} >> CLUSTER LEVEL IS > {cluster_level}")

    # cluster_node = f"C[{';'.join([str(c) for c in nodes])}]"
    graph.add_node(cluster_node, TYPE="CLUS", level=cluster_level, sub_graph=subg)
    for node in nodes:
        # print(f"Contracting NODE {cluster_node} and {node}")
        graph = nx.contracted_nodes(graph, cluster_node, node, self_loops=False)
    # viz_g(graph)

    if save_dict is not None:
        clst_list = save_dict.get(cluster_level, [])
        clst_list.append(
            (
                cluster_node,
                [str(c) for c in subg.nodes if subg.nodes[c].get("TYPE", None) == "PART"],
                [str(c) for c in subg.nodes if subg.nodes[c].get("TYPE", None) == "CONN"],
                [str(c) for c in subg.nodes if subg.nodes[c].get("TYPE", None) == "CLUS"]
            )
        )
        save_dict[cluster_level] = clst_list

    return graph


def process_graph(ass_dep, ass_con):
    new_ass_con = ass_con.copy()
    new_ass_dep = ass_dep.copy()

    new_con_dep = cluster_sccs(new_ass_con, new_ass_dep, 0)

    return new_con_dep


def cluster_sccs(new_ass_con, new_ass_dep, cluster_num):
    new_con_dep = get_con_dep_graph_from_dep(new_ass_dep)
    if nx.is_strongly_connected(new_con_dep):
        raise Exception("Graph is one SCC")

    print(new_con_dep)

    if nx.is_directed_acyclic_graph(new_con_dep):
        export_graph(new_con_dep, "con_dep")
        export_graph(new_ass_con, "ass_con")
        export_graph(new_ass_dep, "ass_dep")
        return new_con_dep

    condensed = nx.condensation(new_con_dep)
    for scc_node in list(nx.topological_sort(condensed)):
        scc = condensed.nodes[scc_node]['members']
        if len(scc) < 2:
            continue
        print(f"Found a SCC -> {scc}")

        # trm_con_dep = new_con_dep.subgraph(scc).copy()
        trm_ass_con = get_dep_graph_from_connections(new_ass_con, scc)
        trm_ass_dep = new_ass_dep.subgraph(trm_ass_con.nodes).copy()
        # viz_g(trm_ass_dep)
        clusters = list(nx.weakly_connected_components(trm_ass_con))
        print(f"Main Clusters: {clusters}")
        seg_ass_dep = nx.union_all([new_ass_dep.subgraph(cluster).copy() for cluster in clusters])
        # viz_g(seg_ass_dep)
        # seg_con_dep = get_con_dep_graph_from_dep(seg_ass_dep)

        # # Remove edges from ConnectionsDependencyGraph
        # for edge in trm_con_dep.edges:
        #     if not seg_con_dep.has_edge(*edge):
        #         new_con_dep.remove_edge(*edge)

        # Remove edges from ConnectionsDependencyGraph
        for edge in trm_ass_dep.edges:
            if not seg_ass_dep.has_edge(*edge):
                print(f"REMOVING EDGE FROM ASS_DEP: {edge}")
                new_ass_dep.remove_edge(*edge)

        for cluster in clusters:
            print(f"Clustering > {cluster}")
            cluster_name = f"CL_{cluster_num:02}"

            clstr_nodes = [n for n in cluster if new_con_dep.has_node(n)]
            print(f"{cluster_name} > {cluster} > CON Nodes > {clstr_nodes}")

            # Update Graphs
            # new_con_dep = collapse_nodes(new_con_dep, clstr_nodes, cluster_name)
            new_ass_con = collapse_nodes(new_ass_con, cluster, cluster_name, save_dict=clusters_dict)
            new_ass_dep = collapse_nodes(new_ass_dep, cluster, cluster_name)

            cluster_num += 1

    print(f"\n\nIS DAG: {nx.is_directed_acyclic_graph(new_con_dep)}\n\n")
    return cluster_sccs(new_ass_con, new_ass_dep, cluster_num)


def replace_cluster_with_conns(graph: nx.DiGraph):
    all_clusters = [n for n, t in graph.nodes.data("TYPE") if t == "CLUS"]
    print('=' * 100)
    print(graph)
    print(all_clusters)
    if not all_clusters:
        return graph

    # Replace clusters with connections and internal clusters
    for cluster in all_clusters:
        print('-' * 10)
        print(cluster)
        print(graph.nodes[cluster])
        print(graph.nodes[cluster]["contraction"])

        preds = list(graph.predecessors(cluster))
        succs = list(graph.successors(cluster))
        print(preds)
        print(succs)

        for succ in succs:
            for pred in preds:
                graph.add_edge(pred, succ)

        cluster_con_dep = get_con_dep_graph_from_dep(graph.nodes[cluster]["sub_graph"])
        # viz_g(cluster_con_dep)

        graph.add_nodes_from(
            [(n, d) for n, d in graph.nodes[cluster]["contraction"].items() if d["TYPE"] != "PART"])

        if cluster_con_dep.size() > 0:
            viz_g(cluster_con_dep)
            graph.add_edges_from(cluster_con_dep.edges)

        sub_clusters = [n for n, d in graph.nodes[cluster]["contraction"].items() if d["TYPE"] == "CLUS"]
        children_con = [n for n, d in graph.nodes[cluster]["contraction"].items() if d["TYPE"] == "CONN"]
        print(f"SUB CLUSTERS > {sub_clusters}")
        print(f"CHILDREN CON > {children_con}")

        for sub_cluster in sub_clusters:
            print(" >> ", sub_cluster)
            for child_con in children_con:
                graph.add_edge(sub_cluster, child_con)
            for pred in preds:
                graph.add_edge(pred, sub_cluster)
            for succ in succs:
                graph.add_edge(sub_cluster, succ)
            print(list(graph.successors(sub_cluster)))

        for child in children_con:
            print(" >> ", child)
            for succ in succs:
                graph.add_edge(child, succ)
            print(list(graph.successors(child)))

        graph.remove_node(cluster)

    return replace_cluster_with_conns(graph)


def export_graph(g, name):
    nx.nx_agraph.to_agraph(g).draw(f"exports/{name}.pdf", prog="dot")


subax1 = plt.subplot()
export_graph(dep, "dep")

clusters_dict = {}
final_con = process_graph(dep, con)
print(clusters_dict)

export_graph(final_con, "res_clustered")

print("#" * 1000)
final_con = replace_cluster_with_conns(final_con)

export_graph(final_con, "res_expanded")
print("FIN")

# Exports
stage = 0
layers_dict = {}
all_parts = []
while final_con.order() > 0:
    print(final_con)

    sources = [x for x, ind in final_con.in_degree if ind == 0]
    print(sources)
    if not sources:
        print("FUCK . . . No Sources")
        viz_g(final_con)
    con_graph = get_dep_graph_from_connections(con, sources)

    # Export
    layers_dict[stage] = {}
    component_count = 0
    for component in nx.weakly_connected_components(con_graph):
        print(component)
        layers_dict[stage][component_count] = {}
        comp_conns = [n for n in component if con_graph.nodes[n]["TYPE"] == "CONN"]
        comp_parts = [n for n in component if con_graph.nodes[n]["TYPE"] == "PART"]
        comp_added = [p for p in comp_parts if p not in all_parts]
        all_parts += comp_added

        print("Filling Components:")
        comp_group = set(comp_parts)
        for layer in layers_dict.keys():
            if layer >= stage:
                continue
            for cmp_name in layers_dict[layer].keys():
                if any([prt in layers_dict[layer][cmp_name]["parts"] for prt in comp_parts]):
                    print(f"COMPONENT IS EXTENDING {layer}-{cmp_name}")
                    comp_group.update(layers_dict[layer][cmp_name]["parts"])

        layers_dict[stage][component_count]["conns"] = comp_conns
        layers_dict[stage][component_count]["parts"] = comp_parts
        layers_dict[stage][component_count]["added"] = comp_added
        layers_dict[stage][component_count]["group"] = comp_group

        component_count += 1
    # layers_dict[stage] = sources
    final_con.remove_nodes_from(sources)
    stage += 1

print(layers_dict)

with open("exports/export-components.csv", 'w') as file:
    for stg in layers_dict.keys():
        for cmp in layers_dict[stg]:
            comp = layers_dict[stg][cmp]
            file.write(
                f"{stg:02},{cmp:02},{';'.join(comp['conns'])},{';'.join(comp['parts'])},{';'.join(comp['added'])},{';'.join(comp['group'])}\n")

with open("exports/export-clusters.csv", 'w') as file:
    for lay in clusters_dict.items():
        for clst in lay[1]:
            file.write(f"{lay[0]},{clst[0]},{';'.join(clst[1])},{';'.join(clst[2])},{';'.join(clst[3])}\n")
