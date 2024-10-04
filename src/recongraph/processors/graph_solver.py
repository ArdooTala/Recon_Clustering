import networkx as nx
import logging


logger = logging.getLogger(__name__)
clusters_dict = {}

def convert_ass_dep_to_con_dep(dep_graph, drop_types=None):
    if not drop_types:
        drop_types = ["PART"]

    con_dep = dep_graph.copy()
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
    graph = graph.copy()
    subg = graph.subgraph(nodes).copy()
    cluster_level_data = subg.nodes.data('level', default=-1)
    cluster_level = max([lvl for _, lvl in cluster_level_data]) + 1
    logger.info(f"\t>> ADDING CLUSTER: {cluster_node} > CLUSTER LEVEL: {cluster_level} > NODES: {nodes}")

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
        raise Exception("Graph is one SCC")

    if nx.is_directed_acyclic_graph(new_ass_dep):
        print("Graph is DAG...")
        logger.info("Graph is DAG. Exiting Solution.")
        return new_ass_dep

    logger.info(f"CLUSTERING...{new_ass_dep}")

    condensed = nx.condensation(new_ass_dep)
    for scc_node in list(nx.topological_sort(condensed)):
        cluster_nodes = condensed.nodes[scc_node]['members']
        if len(cluster_nodes) < 2:
            continue
        logger.debug(f"Found a SCC: {cluster_nodes}")
        for i in range(10):
            extended_ass_dep = extend_sub_graph_with_parts(new_ass_dep, cluster_nodes)

            cluster_nodes = list(extended_ass_dep.nodes)
            logger.debug(f"EXTENDED SUBGRAPH: {cluster_nodes}")

            temp_ass_dep = collapse_nodes(new_ass_dep, cluster_nodes, -1)
            all_sccs = nx.strongly_connected_components(temp_ass_dep)
            extended_nodes = [list(g) for g in all_sccs if -1 in g][0]
            if len(extended_nodes) > 1:
                extended_nodes.remove(-1)
                logger.debug(f"Found extended nodes: {extended_nodes}")
                cluster_nodes = set(cluster_nodes)
                cluster_nodes.update(extended_nodes)
                cluster_nodes = list(cluster_nodes)
                logger.debug(f"\tExtending > [{i}]: Latest EXTENDED Nodes: {cluster_nodes}")
            else:
                logger.debug(f"Extended {i} times. Final EXTENDED Nodes: {cluster_nodes}")
                break

        trm_ass_dep = new_ass.subgraph(cluster_nodes)
        trm_ass_con = nx.subgraph_view(
            trm_ass_dep,
            filter_edge=lambda e1, e2: trm_ass_dep[e1][e2]["EDGE_TYPE"] != "COLL",
        )
        clusters = list(nx.weakly_connected_components(trm_ass_con))
        logger.info(f"Splitting the SCC to {len(clusters)} Clusters: {clusters}")
        seg_ass_dep = nx.union_all([new_ass_dep.subgraph(cluster) for cluster in clusters])

        # Remove edges from ConnectionsDependencyGraph
        edges_to_remove = [edge for edge in trm_ass_dep.edges if not seg_ass_dep.has_edge(*edge)]
        logger.info(f"\tRemoving {len(edges_to_remove)} Edges from the graph: {edges_to_remove}")
        assert all([new_ass_dep.edges[e]['EDGE_TYPE'] == 'COLL' for e in edges_to_remove])
        new_ass_dep.remove_edges_from(edges_to_remove)

        for cluster in clusters:
            cluster_name = f"CL_{cluster_num:02}"
            logger.info(f"Cluster: {cluster_name} > {cluster}")

            # Update Graphs
            new_ass_dep = collapse_nodes(new_ass_dep, cluster, cluster_name, save_dict=clusters_dict)

            cluster_num += 1

        logger.info(f"Is DAG yet: {nx.is_directed_acyclic_graph(new_ass_dep)}")
        return direct_cluster_sccs(new_ass_dep, cluster_num)


def _expands_cluster(graph, cluster):
    cluster_con_dep = graph.nodes[cluster]["sub_graph"]
    logger.debug(f"\tEXPANDING CLUSTER: {cluster} > {cluster_con_dep} > {cluster_con_dep.nodes}")

    if len(cluster_con_dep) < 1:
        raise Exception("Cluster is empty")

    if not nx.is_directed_acyclic_graph(cluster_con_dep):
        raise Exception("CLUSTER IS NOT DAG, NEEDS SOLUTION")

    preds = list(graph.predecessors(cluster))
    succs = list(graph.successors(cluster))
    logger.debug(f"\t\tPREDS: {preds}")
    logger.debug(f"\t\tSUCCS: {succs}")

    logger.debug(f"\t\tCLUSTER INTERNAL NODES: {cluster_con_dep.nodes}")

    logger.debug(f"\t\tReplacing Cluster {cluster} with internal connections graph")
    graph.add_nodes_from(cluster_con_dep.nodes.items())
    graph.add_edges_from(cluster_con_dep.edges)

    sources = [x for x, ind in cluster_con_dep.in_degree if ind == 0]
    logger.debug(f"\t\tSOURCE NODES: {sources}")
    for source in sources:
        logger.debug(f"\t\t\tConnecting SOURCE NODE {source} to {preds}")
        for pred in preds:
            graph.add_edge(source, pred)

    sinks = [x for x, ind in cluster_con_dep.out_degree if ind == 0]
    logger.debug(f"\t\tSINK NODES: {sinks}")
    for sink in sinks:
        logger.debug(f"\t\t\tConnecting SINK NODE {sink} to {succs}")
        for succ in succs:
            graph.add_edge(sink, succ)

    graph.remove_node(cluster)

    return graph


def expand_clusters(graph: nx.DiGraph):
    all_clusters = [n for n, t in graph.nodes.data("TYPE") if t == "CLUS"]
    logger.info(f"Expanding clusters {all_clusters} in a {graph}")
    if not all_clusters:
        return graph

    for cluster in all_clusters:
        _expands_cluster(graph, cluster)

    return replace_clusters_with_conns(graph)


def _replace_cluster_with_conns(graph, cluster):
    cluster_con_dep = graph.nodes[cluster]["sub_graph"]
    logger.debug(f"\tEXPANDING CLUSTER: {cluster} > {cluster_con_dep} > {cluster_con_dep.nodes}")

    if len(cluster_con_dep) < 1:
        raise Exception("Cluster is empty")

    if not nx.is_directed_acyclic_graph(cluster_con_dep):
        raise Exception("CLUSTER IS NOT DAG, NEEDS SOLUTION")

    preds = list(graph.predecessors(cluster))
    succs = list(graph.successors(cluster))
    logger.debug(f"\t\tPREDS: {preds}")
    logger.debug(f"\t\tSUCCS: {succs}")

    cluster_con_dep = convert_ass_dep_to_con_dep(cluster_con_dep)
    logger.debug(f"\t\tCLUSTER INTERNAL NODES: {cluster_con_dep.nodes}")

    logger.debug(f"\t\tReplacing Cluster {cluster} with internal connections graph")
    graph.add_nodes_from(cluster_con_dep.nodes.items())
    graph.add_edges_from(cluster_con_dep.edges)

    sources = [x for x, ind in cluster_con_dep.in_degree if ind == 0]
    logger.debug(f"\t\tSOURCE NODES: {sources}")
    for source in sources:
        logger.debug(f"\t\t\tConnecting SOURCE NODE {source} to {preds}")
        for pred in preds:
            graph.add_edge(source, pred)

    sinks = [x for x, ind in cluster_con_dep.out_degree if ind == 0]
    logger.debug(f"\t\tSINK NODES: {sinks}")
    for sink in sinks:
        logger.debug(f"\t\t\tConnecting SINK NODE {sink} to {succs}")
        for succ in succs:
            graph.add_edge(sink, succ)

    graph.remove_node(cluster)

    return graph


def replace_clusters_with_conns(graph: nx.DiGraph):
    all_clusters = [n for n, t in graph.nodes.data("TYPE") if t == "CLUS"]
    logger.info(f"REPLACING CLUSTERS: {all_clusters} in a {graph}")
    if not all_clusters:
        return graph

    for cluster in all_clusters:
        _replace_cluster_with_conns(graph, cluster)

    return replace_clusters_with_conns(graph)


def generate_stages_graph(g, stages_dict):
    stages_graph = g.copy()
    for stg in stages_dict.keys():
        for grp in stages_dict[stg].keys():
            grp_conns = stages_dict[stg][grp]["conns"]
            stages_graph = collapse_nodes(stages_graph, grp_conns, f"{stg}_{grp}")

    return stages_graph
