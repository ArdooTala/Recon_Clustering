import networkx as nx
import matplotlib.pyplot as plt
import pygraphviz as pgv
# from example_graph import con, dep
from main import con, dep


def viz_g(g):
    nx.draw_circular(g, with_labels=True, font_weight='bold')
    plt.show()


def get_con_dep_graph_from_ass_dep(dep_graph, drop_types=None):
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
        elems.update(list(graph.predecessors(no)))
    return graph.subgraph(list(elems) + list(nodes)).copy()


def add_parts_to_sub_graph(graph, nodes):
    elems = set(nodes)
    for no in nodes:
        if graph.nodes[no]["TYPE"] == 'PART':
            continue
        elems.update([prd for prd in graph.predecessors(no) if graph.nodes[prd]["TYPE"] != 'CONN'])
    return graph.subgraph(list(elems)).copy()


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


def direct_cluster_sccs(new_ass_con, new_ass_dep, cluster_num):
    if nx.is_strongly_connected(new_ass_dep):
        print("ERROR")
        viz_g(new_ass_dep)
        raise Exception("Graph is one SCC")

    if nx.is_directed_acyclic_graph(new_ass_dep):
        print("CON_DEP graph is a DAG...")
        export_graph(new_ass_con, "direct_ass_con")
        export_graph(new_ass_dep, "direct_ass_dep")
        return new_ass_dep

    print(f"CLUSTERING...{new_ass_dep}")

    condensed = nx.condensation(new_ass_dep)
    for scc_node in list(nx.topological_sort(condensed)):
        cluster_nodes = condensed.nodes[scc_node]['members']
        if len(cluster_nodes) < 2:
            continue
        print(f"CON_DEP SCC: {cluster_nodes}")
        for i in range(10):
            extended_ass_dep = add_parts_to_sub_graph(new_ass_dep, cluster_nodes)

            # viz_g(trm_ass_dep)
            # viz_g(extended_ass_dep)
            # viz_g(nx.condensation(extended_ass_dep))

            cluster_nodes = list(extended_ass_dep.nodes)
            print(f"ASS_DEP Nodes: {cluster_nodes}")

            temp_ass_dep = collapse_nodes(new_ass_dep.copy(), cluster_nodes, -1)
            all_sccs = nx.strongly_connected_components(temp_ass_dep)
            extended_nodes = [list(g) for g in all_sccs if -1 in g][0]
            if len(extended_nodes) > 1:
                extended_nodes.remove(-1)
                print(f"Found extended nodes: {extended_nodes}")
                cluster_nodes = set(cluster_nodes)
                cluster_nodes.update(extended_nodes)
                cluster_nodes = list(cluster_nodes)
                print(f"\tExtending > [{i}]: Latest ASS_DEP Nodes: {cluster_nodes}")
            else:
                print(f"Extended {i} times. Final ASS_DEP Nodes: {cluster_nodes}")
                break

        trm_ass_dep = new_ass_dep.subgraph(cluster_nodes).copy()
        trm_ass_con = new_ass_con.subgraph(cluster_nodes).copy()
        clusters = list(nx.weakly_connected_components(trm_ass_con))
        print(f"Segmenting SCC to {len(clusters)} Clusters: {clusters}")
        seg_ass_dep = nx.union_all([new_ass_dep.subgraph(cluster).copy() for cluster in clusters])

        # Remove edges from ConnectionsDependencyGraph
        edges_to_remove = [edge for edge in trm_ass_dep.edges if not seg_ass_dep.has_edge(*edge)]
        print(f"\tRemoving {len(edges_to_remove)} Edges from ASS_DEP: {edges_to_remove}")
        print(f"\t\tAll are COLL: {all([new_ass_dep.edges[e]['EDGE_TYPE'] == 'COLL' for e in edges_to_remove])}")
        new_ass_dep.remove_edges_from(edges_to_remove)

        for cluster in clusters:
            cluster_name = f"CL_{cluster_num:02}"
            print(f"{cluster_name} > {cluster}")

            # Update Graphs
            new_ass_con = collapse_nodes(new_ass_con, cluster, cluster_name, save_dict=clusters_dict)
            new_ass_dep = collapse_nodes(new_ass_dep, cluster, cluster_name)

            cluster_num += 1

        print(f"Is DAG yet: {nx.is_directed_acyclic_graph(new_ass_dep)}\n\n")
        return direct_cluster_sccs(new_ass_con, new_ass_dep, cluster_num)


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
        print(f"PREDS: {preds}")
        print(f"SUCCS: {succs}")

        for succ in succs:
            for pred in preds:
                graph.add_edge(pred, succ)

        # graph.add_nodes_from(
        #     [(n, d) for n, d in graph.nodes[cluster]["contraction"].items() if d["TYPE"] != "PART"])

        cluster_con_dep = graph.nodes[cluster]["sub_graph"]
        print(cluster_con_dep.nodes)
        cluster_con_dep = get_con_dep_graph_from_ass_dep(cluster_con_dep)
        print(cluster_con_dep.nodes)

        if not nx.is_directed_acyclic_graph(cluster_con_dep):
            print("#" * 200)
            viz_g(cluster_con_dep)

        graph.add_nodes_from(cluster_con_dep.nodes.items())
        graph.add_edges_from(cluster_con_dep.edges)

        sinks = [x for x, ind in cluster_con_dep.out_degree if ind == 0]

        sub_clusters = [n for n, d in graph.nodes[cluster]["contraction"].items() if d["TYPE"] == "CLUS"]
        print(f"SUB CLUSTERS > {sub_clusters}")

        for sub_cluster in sub_clusters:
            print(" >> ", graph.in_degree[sub_cluster], " >> ", graph.out_degree[sub_cluster])
            # for child_con in children_con:
            #     graph.add_edge(sub_cluster, child_con)
            for pred in preds:
                graph.add_edge(pred, sub_cluster)
            for succ in succs:
                graph.add_edge(sub_cluster, succ)
            print(list(graph.successors(sub_cluster)))

        for sink in sinks:
            print(" >> ", sink)
            for succ in succs:
                graph.add_edge(sink, succ)
            print(list(graph.successors(sink)))

        graph.remove_node(cluster)

    return replace_cluster_with_conns(graph)


def export_graph(g, name):
    # nx.nx_agraph.to_agraph(g).draw(f"exports/{name}.pdf", prog="neato",
    #                                args="-Gdiredgeconstraints=true -Gmode='ipsep' -Goverlap='prism5000'")
    nx.nx_agraph.to_agraph(g).draw(f"exports/{name}.pdf", prog="dot",
                                   args="-Grankdir='LR' -Granksep=1.5 -Gsplines='false'")


def generate_gantt(graph):
    if not nx.is_directed_acyclic_graph(graph):
        raise Exception("Gantt cannot be generated because the graph is not a DAG")

    gantt_dict = {}
    step = 0
    print("Calculating forward run")
    forward_graph = graph.copy()
    while forward_graph.order() > 0:
        sources = [x for x, ind in forward_graph.in_degree if ind == 0]
        for source in sources:
            gantt_dict[source] = {}
            gantt_dict[source]["start"] = step
            gantt_dict[source]["deps"] = list(graph.predecessors(source))
            gantt_dict[source]["children"] = list(graph.successors(source))

        step += 1
        forward_graph.remove_nodes_from(sources)

    print("Calculating return run")
    return_graph = graph.copy()
    while return_graph.order() > 0:
        sinks = [x for x, ind in return_graph.out_degree if ind == 0]
        for sink in sinks:
            gantt_dict[sink]["end"] = min(
                [step, ] + [e[1]["start"] for e in gantt_dict.items() if e[0] in gantt_dict[sink]["children"]])

        return_graph.remove_nodes_from(sinks)

    print("Calculating backward run")
    backward_graph = graph.copy()
    while backward_graph.order() > 0:
        print(backward_graph.order())
        sinks = [x for x, ind in backward_graph.out_degree if ind == 0]
        for sink in sinks:
            gantt_dict[sink]["latest"] = step

        step -= 1
        backward_graph.remove_nodes_from(sinks)

    return gantt_dict


def export_stages(graph):
    graph = graph.copy()
    stage = 0
    layer_dict = {}
    all_parts = []

    while graph.order() > 0:
        print(graph)

        sources = [x for x, ind in graph.in_degree if ind == 0]
        print(f"Source Nodes: {sources}")
        if not sources:
            raise Exception("FUCK!...No Sources in Graph")
        con_graph = get_dep_graph_from_connections(con, sources)

        # Export
        layer_dict[stage] = {}
        component_count = 0
        for component in nx.weakly_connected_components(con_graph):
            print(f"\tComponent: {component}")
            layer_dict[stage][component_count] = {}
            comp_conns = [n for n in component if con_graph.nodes[n]["TYPE"] == "CONN"]
            comp_parts = [n for n in component if con_graph.nodes[n]["TYPE"] == "PART"]
            comp_added = [p for p in comp_parts if p not in all_parts]
            all_parts += comp_added

            comp_group = set(comp_parts)

            if stage > 0:
                ext_clstrs = []
                for cmp_name in layer_dict[stage - 1].keys():
                    if any([prt in layer_dict[stage - 1][cmp_name]["group"] for prt in comp_parts]):
                        comp_group.update(layer_dict[stage - 1][cmp_name]["group"])
                        ext_clstrs.append(f"{stage}-{cmp_name}")
                print(f"\t\tComponent Extends Clusters > {ext_clstrs}")

            layer_dict[stage][component_count]["conns"] = comp_conns
            layer_dict[stage][component_count]["parts"] = comp_parts
            layer_dict[stage][component_count]["added"] = comp_added
            layer_dict[stage][component_count]["group"] = comp_group

            component_count += 1
        # layer_dict[stage] = sources
        graph.remove_nodes_from(sources)
        stage += 1

    return layer_dict


subax1 = plt.subplot()
export_graph(dep, "dep")

clusters_dict = {}
final_ass = direct_cluster_sccs(con.copy(), dep.copy(), 0)
export_graph(final_ass, "res_dep")
final_con = get_con_dep_graph_from_ass_dep(final_ass)

export_graph(final_con, "res_clustered")
print(clusters_dict)

final_con = replace_cluster_with_conns(final_con)
export_graph(final_con, "res_expanded")

gantt = generate_gantt(final_con)
with open("exports/export-gantt.csv", 'w') as file:
    for el in gantt.items():
        file.write(
            f"{el[0]},{el[1]['start']},{el[1]['end']},{';'.join(el[1]['deps'])},{';'.join(el[1]['children'])}\n")

layers_dict = export_stages(final_con)
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

final_con_copy = final_con.copy()
for stg in layers_dict.keys():
    for grp in layers_dict[stg].keys():
        grp_conns = layers_dict[stg][grp]["conns"]
        final_con_copy = collapse_nodes(final_con_copy, grp_conns, f"{stg}_{grp}")
export_graph(final_con_copy, "stages_dep")

stages_gantt = generate_gantt(final_con_copy)
with open("exports/export-stage_gantt.csv", 'w') as file:
    for el in stages_gantt.items():
        file.write(
            f"{el[0]},{el[1]['start']},{el[1]['end']},{el[1]['latest']},{';'.join(el[1]['deps'])},{';'.join(el[1]['children'])}\n")

nx.write_gexf(dep, f"exports/dep.gexf")

print("FIN")
