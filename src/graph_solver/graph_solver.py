import networkx as nx


clusters_dict = {}


def convert_ass_dep_to_con_dep(dep_graph, drop_types=None):
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


def extend_sub_graph_with_parts(graph, nodes):
    nodes_set = set(nodes)
    for no in nodes:
        if graph.nodes[no]["TYPE"] == 'PART':
            continue
        nodes_set.update([prd for prd in graph.predecessors(no) if graph.nodes[prd]["TYPE"] != 'CONN'])
    return graph.subgraph(list(nodes_set)).copy()


def collapse_nodes(graph, nodes, cluster_node, save_dict=None):
    subg = graph.subgraph(nodes).copy()
    cluster_level_data = subg.nodes.data('level', default=-1)
    cluster_level = max([lvl for _, lvl in cluster_level_data]) + 1
    print(f"\t>> ADDING CLUSTER: {cluster_node} > CLUSTER LEVEL: {cluster_level} > NODES: {nodes}")

    graph.add_node(cluster_node, TYPE="CLUS", level=cluster_level, sub_graph=subg)
    for node in nodes:
        graph = nx.contracted_nodes(graph, cluster_node, node, self_loops=False)

    if save_dict is not None:
        clusters_list = save_dict.get(cluster_level, [])
        clusters_list.append(
            (
                cluster_node,
                [str(c) for c in subg.nodes if subg.nodes[c].get("TYPE", None) == "PART"],
                [str(c) for c in subg.nodes if subg.nodes[c].get("TYPE", None) == "CONN"],
                [str(c) for c in subg.nodes if subg.nodes[c].get("TYPE", None) == "CLUS"]
            )
        )
        save_dict[cluster_level] = clusters_list

    return graph


def direct_cluster_sccs(new_ass: nx.DiGraph, cluster_num=0):
    new_ass_dep = new_ass.copy()

    if nx.is_strongly_connected(new_ass_dep):
        print("ERROR")
        raise Exception("Graph is one SCC")

    if nx.is_directed_acyclic_graph(new_ass_dep):
        print("CON_DEP graph is a DAG...\n")
        return new_ass_dep

    print(f"CLUSTERING...{new_ass_dep}")

    condensed = nx.condensation(new_ass_dep)
    for scc_node in list(nx.topological_sort(condensed)):
        cluster_nodes = condensed.nodes[scc_node]['members']
        if len(cluster_nodes) < 2:
            continue
        print(f"ASSEMBLY GRAPH SCC: {cluster_nodes}")
        for i in range(10):
            extended_ass_dep = extend_sub_graph_with_parts(new_ass_dep, cluster_nodes)

            cluster_nodes = list(extended_ass_dep.nodes)
            print(f"EXTENDED SUBGRAPH: {cluster_nodes}")

            temp_ass_dep = collapse_nodes(new_ass_dep, cluster_nodes, -1)
            all_sccs = nx.strongly_connected_components(temp_ass_dep)
            extended_nodes = [list(g) for g in all_sccs if -1 in g][0]
            if len(extended_nodes) > 1:
                extended_nodes.remove(-1)
                print(f"Found extended nodes: {extended_nodes}")
                cluster_nodes = set(cluster_nodes)
                cluster_nodes.update(extended_nodes)
                cluster_nodes = list(cluster_nodes)
                print(f"\tExtending > [{i}]: Latest EXTENDED Nodes: {cluster_nodes}")
            else:
                print(f"Extended {i} times. Final EXTENDED Nodes: {cluster_nodes}")
                break

        trm_ass_dep = new_ass.subgraph(cluster_nodes)
        trm_ass_con = nx.subgraph_view(
            trm_ass_dep,
            filter_edge=lambda e1, e2: trm_ass_dep[e1][e2]["EDGE_TYPE"] != "COLL",
        )
        # trm_ass_con = nx.subgraph_view(
        #     new_ass,
        #     filter_edge=lambda e1, e2: new_ass[e1][e2]["EDGE_TYPE"] != "COLL",
        #     filter_node=lambda n: n in cluster_nodes,
        # ).copy()
        clusters = list(nx.weakly_connected_components(trm_ass_con))
        print(f"Segmenting SCC to {len(clusters)} Clusters: {clusters}")
        seg_ass_dep = nx.union_all([new_ass_dep.subgraph(cluster) for cluster in clusters])

        # Remove edges from ConnectionsDependencyGraph
        edges_to_remove = [edge for edge in trm_ass_dep.edges if not seg_ass_dep.has_edge(*edge)]
        print(f"\tRemoving {len(edges_to_remove)} Edges from ASS_DEP: {edges_to_remove}")
        print(f"\t\tAll are COLL: {all([new_ass_dep.edges[e]['EDGE_TYPE'] == 'COLL' for e in edges_to_remove])}")
        new_ass_dep.remove_edges_from(edges_to_remove)

        for cluster in clusters:
            cluster_name = f"CL_{cluster_num:02}"
            print(f"{cluster_name} > {cluster}")

            # Update Graphs
            new_ass_dep = collapse_nodes(new_ass_dep, cluster, cluster_name, save_dict=clusters_dict)

            cluster_num += 1

        print(f"Is DAG yet: {nx.is_directed_acyclic_graph(new_ass_dep)}\n\n")
        return direct_cluster_sccs(new_ass_dep, cluster_num)


def replace_cluster_with_conns(graph: nx.DiGraph):
    all_clusters = [n for n, t in graph.nodes.data("TYPE") if t == "CLUS"]
    print('=' * 100)
    print(f"REPLACING CLUSTERS: {all_clusters} in a {graph}")
    if not all_clusters:
        return graph

    # Replace clusters with connections and internal clusters
    for cluster in all_clusters:
        cluster_con_dep = graph.nodes[cluster]["sub_graph"]
        print(f"\t{cluster} > {cluster_con_dep} > {cluster_con_dep.nodes}")
        # print(f"\t > {graph.nodes[cluster]}")

        cluster_con_dep = convert_ass_dep_to_con_dep(cluster_con_dep)
        print(f"\t\tCLUSTER INTERNAL CONNECTION NODES: {cluster_con_dep.nodes}")

        if not nx.is_directed_acyclic_graph(cluster_con_dep):
            raise Exception("CLUSTER IS NOT DAG, NEEDS SOLUTION")

        preds = list(graph.predecessors(cluster))
        succs = list(graph.successors(cluster))
        print(f"\t\tPREDS: {preds}")
        print(f"\t\tSUCCS: {succs}")

        for succ in succs:
            for pred in preds:
                graph.add_edge(pred, succ)

        graph.add_nodes_from(cluster_con_dep.nodes.items())
        graph.add_edges_from(cluster_con_dep.edges)

        sub_clusters = [n for n, d in graph.nodes[cluster]["contraction"].items() if d["TYPE"] == "CLUS"]
        print(f"\t\tSUB CLUSTERS: {sub_clusters}")
        for sub_cluster in sub_clusters:
            print(f"\t\t\tSUB CLUSTER: {sub_cluster}")
            for pred in preds:
                graph.add_edge(pred, sub_cluster)
            for succ in succs:
                graph.add_edge(sub_cluster, succ)

        sinks = [x for x, ind in cluster_con_dep.out_degree if ind == 0]
        print(f"\t\tSINK NODES: {sinks}")
        for sink in sinks:
            print(f"\t\t\tSINK NODE: {sink}")
            for succ in succs:
                graph.add_edge(sink, succ)

        graph.remove_node(cluster)

    return replace_cluster_with_conns(graph)


def generate_stages_graph(g, stages_dict):
    stages_graph = g.copy()
    for stg in stages_dict.keys():
        for grp in stages_dict[stg].keys():
            grp_conns = stages_dict[stg][grp]["conns"]
            stages_graph = collapse_nodes(stages_graph, grp_conns, f"{stg}_{grp}")

    return stages_graph
