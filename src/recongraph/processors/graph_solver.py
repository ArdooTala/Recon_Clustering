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
    logger.info(f"\t>> FORMING CLUSTER: {cluster_node} > CLUSTER LEVEL: {cluster_level} > NODES: {nodes}")

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


def resolve_dependencies(graph: nx.DiGraph, cluster_num=0, cluster_level=0):
    ass_dep = graph.copy()

    # Get/Add clusters_dict as a graph attribute
    if 'clusters_dict' not in ass_dep.graph:
        ass_dep.graph['clusters_dict'] = {}
    clusters_dict = ass_dep.graph['clusters_dict']

    if nx.is_directed_acyclic_graph(ass_dep):
        logger.info("Graph is DAG. Exiting Solution.")
        return ass_dep

    if nx.is_strongly_connected(ass_dep):
        raise Exception("Graph is one SCC")

    logger.info(f"Resolving Dependencies in a {ass_dep}")

    reciprocal_dependencies_groups = _find_reciprocal_dependency_groups(graph)
    logger.debug(f"Found {len(reciprocal_dependencies_groups)} groups of reciprocal dependencies")

    for rdg in reciprocal_dependencies_groups:
        logger.debug(f"Solving RECIPROCAL DEPENDENCY GROUP of {len(rdg)} nodes")

        # Remove COLL edges
        trm_ass_dep = graph.subgraph(rdg)
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
            # REPLACE CLUSTER
            cluster_name = f"L{cluster_level:02}_C{cluster_num:02}"
            cluster_num += 1

            logger.info(f"Cluster: {cluster_name} > {cluster}")

            # Update Graphs
            internal_graph = ass_dep.subgraph(cluster)
            logger.debug(f"SOLVING CLUSTER INTERNAL {internal_graph}")

            resolved_internal_graph = resolve_dependencies(internal_graph, cluster_level=cluster_level+1)
            assert nx.is_directed_acyclic_graph(resolved_internal_graph)

            # resolved_cluster_sources = [x for x, ind in resolved_internal_graph.in_degree if ind == 0]
            # assert all([graph.nodes[cls_src]["TYPE"] == "PART" for cls_src in resolved_cluster_sources])
            resolved_cluster_sinks = [x for x, ind in resolved_internal_graph.out_degree if ind == 0]
            assert all([graph.nodes[cls_snk]["TYPE"] == "CONN" for cls_snk in resolved_cluster_sinks])

            # Debug
            cluster_sinks = [x for x, ind in internal_graph.out_degree if ind == 0]
            assert all([graph.nodes[cls_snk]["TYPE"] == "CONN" for cls_snk in resolved_cluster_sinks])
            logger.debug(f"Cluster {cluster_name} sinks          : {cluster_sinks}")
            logger.debug(f"Resolved Cluster {cluster_name} sinks : {resolved_cluster_sinks}")
            logger.debug(f"SAME SINKS: {cluster_sinks == resolved_cluster_sinks}")
            # end Debug

            tmp_graph = _collapse_nodes(ass_dep, cluster, 'cls')
            cluster_successors = list(tmp_graph.successors('cls'))
            logger.debug(f"Cluster {cluster_name} Successors: {cluster_successors}")
            assert all([ass_dep.nodes[succ]['TYPE'] == 'CONN' for succ in cluster_successors])


            logger.debug(f"DONE SOLVING CLUSTER {cluster_name}\n")

            # Replace Cluster
            ass_dep.remove_nodes_from(cluster)
            ass_dep = nx.union(ass_dep, resolved_internal_graph)

            for sink in resolved_cluster_sinks:
                for succ in cluster_successors:
                    ass_dep.add_edge(sink, succ)

        logger.debug(f"Is DAG yet: {nx.is_directed_acyclic_graph(ass_dep)}")

    return ass_dep

        # For each Cluster: Find Connections

def direct_cluster_sccs(new_ass: nx.DiGraph, cluster_num=0):
    new_ass_dep = new_ass.copy()
    if 'clusters_dict' not in new_ass_dep.graph:
        new_ass_dep.graph['clusters_dict'] = {}

    clusters_dict = new_ass_dep.graph['clusters_dict']

    if nx.is_strongly_connected(new_ass_dep):
        raise Exception("Graph is one SCC")

    if nx.is_directed_acyclic_graph(new_ass_dep):
        logger.info("Graph is DAG. Exiting Solution.")
        return new_ass_dep

    logger.info(f"CLUSTERING...{new_ass_dep}")

    condensed = nx.condensation(new_ass_dep)
    for scc_node in list(nx.topological_sort(condensed)):
        cluster_nodes = condensed.nodes[scc_node]['members']
        if len(cluster_nodes) < 2:
            continue
        logger.debug(f"Found a SCC of {len(cluster_nodes)} Nodes > {cluster_nodes}")
        for i in range(10):
            extended_ass_dep = _extract_subgraph_as_cluster(new_ass_dep, cluster_nodes)

            extra_nodes = [n for n in extended_ass_dep.nodes if n not in cluster_nodes]
            logger.debug(f"\tExtending subgraph with {len(extra_nodes)} nodes > {extra_nodes}")
            cluster_nodes = list(extended_ass_dep.nodes)
            logger.debug(f"EXTENDED SUBGRAPH of {len(cluster_nodes)} Nodes > {cluster_nodes}")

            temp_ass_dep = _collapse_nodes(new_ass_dep, cluster_nodes, -1)
            all_sccs = nx.strongly_connected_components(temp_ass_dep)
            extended_nodes = [list(g) for g in all_sccs if -1 in g][0]
            if len(extended_nodes) > 1:
                extended_nodes.remove(-1)
                logger.debug(f"\tFound new SCC including the extended nodes: {extended_nodes}")
                cluster_nodes = set(cluster_nodes)
                cluster_nodes.update(extended_nodes)
                cluster_nodes = list(cluster_nodes)
                logger.debug(f"\tExtending > [{i}]: Latest EXTENDED Nodes: {cluster_nodes}")
            else:
                logger.debug(f"Extended {i+1} times to {len(cluster_nodes)} nodes. Final EXTENDED Nodes: {cluster_nodes}")
                break

        trm_ass_dep = new_ass.subgraph(cluster_nodes)
        trm_ass_con = nx.subgraph_view(
            trm_ass_dep,
            filter_edge=lambda e1, e2: trm_ass_dep[e1][e2]["EDGE_TYPE"] != "COLL",
        )
        clusters = list(nx.weakly_connected_components(trm_ass_con))
        logger.debug(f"Splitting the SCC to {len(clusters)} Clusters: {clusters}")
        seg_ass_dep = nx.union_all([new_ass_dep.subgraph(cluster) for cluster in clusters])

        # Remove edges from ConnectionsDependencyGraph
        edges_to_remove = [edge for edge in trm_ass_dep.edges if not seg_ass_dep.has_edge(*edge)]
        logger.debug(f"\tRemoving {len(edges_to_remove)} Edges from the graph: {edges_to_remove}")
        assert all([new_ass_dep.edges[e]['EDGE_TYPE'] == 'COLL' for e in edges_to_remove])
        new_ass_dep.remove_edges_from(edges_to_remove)

        for cluster in clusters:
            cluster_name = f"CL_{cluster_num:02}"
            logger.info(f"Cluster: {cluster_name} > {cluster}")

            # Update Graphs
            new_ass_dep = _collapse_nodes(new_ass_dep, cluster, cluster_name, save_dict=clusters_dict)

            cluster_num += 1

        logger.debug(f"Is DAG yet: {nx.is_directed_acyclic_graph(new_ass_dep)}")
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
    logger.debug(f"\t\t> PREDECESSORS: {preds}")
    logger.debug(f"\t\t>   SUCCESSORS: {succs}")

    logger.debug(f"\t\tCLUSTER INTERNAL NODES: {cluster_con_dep.nodes}")

    logger.debug(f"\t\tReplacing Cluster {cluster} with internal graph")
    graph.add_nodes_from(cluster_con_dep.nodes.items())
    graph.add_edges_from(cluster_con_dep.edges)

    # Since the cluster is isolated, the predecessors are not a dependency anymore
    # sources = [x for x, ind in cluster_con_dep.in_degree if ind == 0]
    # logger.debug(f"\t\tSOURCE NODES: {sources}")
    # for source in sources:
    #     logger.debug(f"\t\t\tConnecting SOURCE NODE {source} to {preds}")
    #     for pred in preds:
    #         graph.add_edge(source, pred)

    # however, the predecessors and successors need to keep their dependency
    for pred in preds:
        for succ in succs:
            graph.add_edge(pred, succ)

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

    return expand_clusters(graph)


def generate_stages_graph(g, stages_dict):
    stages_graph = g.copy()
    for stg in stages_dict.keys():
        for grp in stages_dict[stg].keys():
            grp_conns = stages_dict[stg][grp]["conns"]
            stages_graph = _collapse_nodes(stages_graph, grp_conns, f"{stg}_{grp}")

    return stages_graph
