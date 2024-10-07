import logging
import networkx as nx


logger = logging.getLogger(__name__)


def _get_dep_graph_from_connections(graph, nodes):
    elems = set()
    for no in nodes:
        elems.update(list(graph.predecessors(no)))
    return graph.subgraph(list(elems) + list(nodes)).copy()


def generate_stages(assembly, con_dep):
    graph = con_dep.copy()
    con = nx.subgraph_view(
        assembly,
        filter_edge=lambda e1, e2: assembly[e1][e2]["EDGE_TYPE"] != "COLL",
    ).copy()
    stages_dict = {}
    all_parts = []

    logger.info("Generating Stages")
    stage = 0
    while graph.order() > 0:
        logger.debug(f"Stage: {stage}")
        sources = [x for x, ind in graph.in_degree if ind == 0]
        logger.debug(f"\tSource Nodes: {sources}")
        if not sources:
            raise Exception("FUCK!...No Sources in Graph")
        con_graph = _get_dep_graph_from_connections(con, sources)

        # Export
        stages_dict[stage] = {}
        component_count = 0
        for component in nx.weakly_connected_components(con_graph):
            logger.debug(f"\t\tComponent: {component}")
            stages_dict[stage][component_count] = {}
            comp_conns = [n for n in component if con_graph.nodes[n]["TYPE"] == "CONN"]
            comp_parts = [n for n in component if con_graph.nodes[n]["TYPE"] == "PART"]
            comp_added = [p for p in comp_parts if p not in all_parts]
            all_parts += comp_added

            for node in comp_conns + comp_parts:
                con.nodes[node]['stage'] = stage
                con.nodes[node]['stage_component'] = component_count

            status_graph = nx.subgraph_view(
                con,
                filter_node=lambda n: (con.nodes(data='stage', default=stage)[n] < stage) or (n in component)
            )
            comp_group = next(wcc for wcc in nx.weakly_connected_components(status_graph) if any([n in wcc for n in comp_parts]))

            # comp_group = set(comp_parts)

            # if stage > 0:
            #     ext_clstrs = []
            #     for cmp_name in stages_dict[stage - 1].keys():
            #         if any([prt in stages_dict[stage - 1][cmp_name]["group"] for prt in comp_parts]):
            #             comp_group.update(stages_dict[stage - 1][cmp_name]["group"])
            #             ext_clstrs.append(f"{stage-1}-{cmp_name}")
            #     logger.debug(f"\t\t\tComponent Extends Clusters > {ext_clstrs}")

            stages_dict[stage][component_count]["conns"] = comp_conns
            stages_dict[stage][component_count]["parts"] = comp_parts
            stages_dict[stage][component_count]["added"] = comp_added
            # stages_dict[stage][component_count]["group"] = comp_group
            stages_dict[stage][component_count]["group"] = [c for c in comp_group if status_graph.nodes(data="TYPE")[c] == "PART"]

            component_count += 1
        # stages_dict[stage] = sources
        graph.remove_nodes_from(sources)
        stage += 1

    return stages_dict


def generate_gantt(graph):
    if not nx.is_directed_acyclic_graph(graph):
        raise Exception("Gantt cannot be generated because the graph is not a DAG")

    gantt_dict = {}
    step = 0
    logger.info("Calculating forward run")
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

    logger.info("Calculating return run")
    return_graph = graph.copy()
    while return_graph.order() > 0:
        sinks = [x for x, ind in return_graph.out_degree if ind == 0]
        for sink in sinks:
            gantt_dict[sink]["end"] = min(
                [step, ] + [e[1]["start"] for e in gantt_dict.items() if e[0] in gantt_dict[sink]["children"]])

        return_graph.remove_nodes_from(sinks)

    logger.info("Calculating backward run")
    backward_graph = graph.copy()
    while backward_graph.order() > 0:
        sinks = [x for x, ind in backward_graph.out_degree if ind == 0]
        for sink in sinks:
            gantt_dict[sink]["latest"] = step

        step -= 1
        backward_graph.remove_nodes_from(sinks)

    return gantt_dict
