import networkx as nx
import logging


logger = logging.getLogger(__name__)

def _convert_ass_dep_to_con_dep(dep_graph, drop_types=None):
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


def _extract_subgraph_as_cluster(graph, nodes):
    nodes_set = set(nodes)
    for no in nodes:
        if graph.nodes[no]["TYPE"] == 'PART':
            continue
        nodes_set.update([prd for prd in graph.predecessors(no) if graph.nodes[prd]["TYPE"] != 'CONN'])
    return graph.subgraph(list(nodes_set)).copy()


def _collapse_nodes(graph, nodes, cluster_node, save_dict=None) -> nx.DiGraph:
    graph = graph.copy()
    subg = graph.subgraph(nodes).copy()
    cluster_level_data = subg.nodes.data('level', default=-1)
    cluster_level = max([lvl for _, lvl in cluster_level_data]) + 1
    logger.info(f"\tCollapsing Nodes into Cluster {cluster_node} with Cluster Level: {cluster_level} > NODES: {nodes}")

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


def _form_reciprocal_dependency_group(graph: nx.DiGraph, subgraph):
    scc_nodes = subgraph.copy()

    for i in range(10):
        extended_ass_dep = _extract_subgraph_as_cluster(graph, scc_nodes)

        extra_nodes = [n for n in extended_ass_dep.nodes if n not in scc_nodes]
        logger.debug(f"\tIncluding {len(extra_nodes)} connected parts > {extra_nodes}")
        scc_nodes = list(extended_ass_dep.nodes)
        # logger.debug(f"\t\tEXTENDED SUBGRAPH of {len(scc_nodes)} Nodes > {scc_nodes}")

        # Check if extending forms another scc
        temp_ass_dep = _collapse_nodes(graph, scc_nodes, -1)
        extended_nodes = [list(g) for g in nx.strongly_connected_components(temp_ass_dep) if -1 in g][0]

        if len(extended_nodes) > 1:
            logger.debug(f"\tFound new SCC including the extended nodes: {extended_nodes}")
            extended_nodes.remove(-1)
            scc_nodes = set(scc_nodes)
            scc_nodes.update(extended_nodes)
            scc_nodes = list(scc_nodes)
            logger.debug(f"\tExtending subgraph to new SCC with {len(extended_nodes)} nodes > {extended_nodes}")
        else:
            logger.debug(f"\tExtended SCC {i} times to {len(scc_nodes)} nodes.")
            logger.debug(f"\tFinal EXTENDED Nodes: {scc_nodes}")
            break
    else:
        raise Exception("Extended the SCC 10 times already. Is there a loop?")

    return scc_nodes


def _find_reciprocal_dependency_groups(graph):
    condensed = nx.condensation(graph)

    # Extend SCCs
    reciprocal_dependencies_groups = []
    for scc in condensed:
        scc_nodes = condensed.nodes[scc]['members']
        if len(scc_nodes) < 2:
            continue
        logger.debug(f"Found a SCC of {len(scc_nodes)} Nodes > {scc_nodes}")

        reciprocal_dependencies_groups.append(
            _form_reciprocal_dependency_group(graph, scc_nodes)
        )

    rdgs_nodes = [n for rdg in reciprocal_dependencies_groups for n in rdg]
    logger.debug(f"FOUND {len(reciprocal_dependencies_groups)} RECIPROCAL DEPENDENCY GROUPS > # of Nodes/Unique Nodes: {len(rdgs_nodes)}/{len(set(rdgs_nodes))}")

    reciprocal_dependencies_subgraph = graph.subgraph(
        set(rdgs_nodes)
    )
    reciprocal_dependencies_wccs = list(nx.weakly_connected_components(reciprocal_dependencies_subgraph))
    logger.debug(f"RECIPROCAL DEPENDENCIES SUBGRAPH is a {reciprocal_dependencies_subgraph} with {len(reciprocal_dependencies_wccs)} connected components")

    return reciprocal_dependencies_wccs


def _resolve_cluster(graph, cluster):
    ass_dep = graph.copy()

    internal_graph = ass_dep.subgraph(cluster).copy()
    logger.debug(f">> SOLVING CLUSTER'S INTERNAL GRAPH {internal_graph}")

    resolved_internal_graph = resolve_dependencies(internal_graph)
    assert nx.is_directed_acyclic_graph(resolved_internal_graph)

    resolved_cluster_sinks = [x for x, ind in resolved_internal_graph.out_degree if ind == 0]
    assert all([graph.nodes[cls_snk]["TYPE"] == "CONN" for cls_snk in resolved_cluster_sinks])

    cluster_successors = set(
        [succ for node in internal_graph for succ in ass_dep.successors(node) if succ not in internal_graph]
    )

    # Assert the cluster is a source
    cluster_predecessors = set(
        [pred for node in internal_graph for pred in ass_dep.predecessors(node) if pred not in internal_graph]
    )
    assert len(cluster_predecessors) == 0

    logger.debug(f"Cluster Successors: {cluster_successors}")
    assert all([ass_dep.nodes[succ]['TYPE'] == 'CONN' for succ in cluster_successors])

    logger.debug(f"<< DONE SOLVING CLUSTER")

    # Replace Cluster
    ass_dep.remove_edges_from(internal_graph.edges)
    ass_dep.add_edges_from(resolved_internal_graph.edges.data())

    for sink in resolved_cluster_sinks:
        for succ in cluster_successors:
            ass_dep.add_edge(sink, succ, EDGE_TYPE='EXTR', color='blue')

    return ass_dep


def _resolve_reciprocal_dependency_group(graph, rdg):
    ass_dep = graph.copy()
    logger.debug(f"Solving RECIPROCAL DEPENDENCY GROUP of {len(rdg)} nodes")

    # Remove COLL edges
    trm_ass_dep = ass_dep.subgraph(rdg)
    trm_ass_con = nx.subgraph_view(
        trm_ass_dep,
        filter_edge=lambda e1, e2: trm_ass_dep[e1][e2]["EDGE_TYPE"] != "COLL",
    )
    clusters = list(nx.weakly_connected_components(trm_ass_con))
    logger.debug(f"\tSplitting the RECIPROCAL DEPENDENCY GROUP to {len(clusters)} Clusters: {clusters}")
    seg_ass_dep = nx.union_all([graph.subgraph(cluster) for cluster in clusters])

    # Remove edges from ConnectionsDependencyGraph
    edges_to_remove = [edge for edge in trm_ass_dep.edges if not seg_ass_dep.has_edge(*edge)]
    assert all([graph.edges[e]['EDGE_TYPE'] == 'COLL' for e in edges_to_remove])
    logger.debug(f"\tRemoving {len(edges_to_remove)} Collision Edges between clusters: {edges_to_remove}")
    ass_dep.remove_edges_from(edges_to_remove)

    for cluster in clusters:
        ass_dep = _resolve_cluster(ass_dep, cluster)

    return ass_dep


def resolve_dependencies(graph: nx.DiGraph):
    ass_dep = graph.copy()

    if nx.is_directed_acyclic_graph(ass_dep):
        logger.info("Graph is DAG. Exiting Solution.")
        return ass_dep

    if nx.is_strongly_connected(ass_dep):
        raise Exception("Graph is one SCC")

    logger.info(f"Resolving Dependencies in a {ass_dep}")

    reciprocal_dependencies_groups = _find_reciprocal_dependency_groups(graph)
    logger.debug(f"Found {len(reciprocal_dependencies_groups)} groups of reciprocal dependencies")

    for rdg in reciprocal_dependencies_groups:
        ass_dep = _resolve_reciprocal_dependency_group(ass_dep, rdg)
        logger.debug(f"Is DAG: {nx.is_directed_acyclic_graph(ass_dep)}")

    return ass_dep


def generate_stages_graph(g, stages_dict):
    stages_graph = g.copy()
    for stg in stages_dict.keys():
        for grp in stages_dict[stg].keys():
            grp_conns = stages_dict[stg][grp]["conns"]
            stages_graph = _collapse_nodes(stages_graph, grp_conns, f"{stg}_{grp}")

    return stages_graph
