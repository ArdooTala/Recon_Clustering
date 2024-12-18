import logging
from pprint import pprint
import networkx as nx
from recongraph.processors import graph_solver


logger = logging.getLogger(__name__)


def _ass_to_con(dep_graph):
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


def _ass_2_con(dep_graph):
    tc = nx.transitive_closure_dag(dep_graph)
    con_dep = nx.subgraph_view(
        tc,
        filter_node=lambda n: tc.nodes.data("TYPE", default=None)[n] != 'PART'
    )
    return con_dep


def _convert_ass_dep_to_con_dep(dep_graph):
    return _ass_2_con(dep_graph)


def _get_dep_graph_from_connections(graph, nodes):
    elems = set()
    for no in nodes:
        elems.update(list(graph.predecessors(no)))
    return graph.subgraph(list(elems) + list(nodes)).copy()


def add_stages(graph: nx.DiGraph):
    assert nx.is_directed_acyclic_graph(graph)

    res_con = _convert_ass_dep_to_con_dep(graph)
    logger.debug(f"Longest Path Length: {nx.dag_longest_path_length(res_con)}")

    # Earliest
    stages = list(nx.topological_generations(res_con))
    for stage, nodes in enumerate(stages):
        for node in nodes:
            graph.nodes[node]["earliest_stage"] = stage
    logger.info(f"Generated {len(stages)} earliest stages > # of connections in each stage: {list(map(len, stages))}")

    # Latest
    stages = list(nx.topological_generations(res_con.reverse()))
    stages.reverse()
    for stage, nodes in enumerate(stages):
        for node in nodes:
            graph.nodes[node]["latest_stage"] = stage
    logger.info(f"Generated {len(stages)} latest stages   > # of connections in each stage: {list(map(len, stages))}")

    for node in graph.nodes:
        if graph.nodes[node]["TYPE"] == "CONN":
            continue

        conns = graph.subgraph([n for n in graph.neighbors(node) if graph.nodes[n]["TYPE"] == "CONN"])
        if not conns:
            raise Exception("PART has no CONN successors!")

        graph.nodes[node]["earliest_stage"] = min([s[1] for s in list(conns.nodes.data("earliest_stage"))])
        graph.nodes[node]["latest_stage"] = min([s[1] for s in list(conns.nodes.data("latest_stage"))])
        logger.debug(f"Node: {node} > Stage: {graph.nodes[node]['earliest_stage']} => {graph.nodes[node]['latest_stage']}")

    return range(len(stages))


def add_components(graph, stage_attr="latest_stage"):
    assert nx.is_directed_acyclic_graph(graph)

    longest_path = graph.subgraph(nx.dag_longest_path(graph))
    stages = sorted(set([s[1] for s in longest_path.nodes.data(stage_attr)]))
    components_dict = {s: [] for s in stages}
    logger.debug(f"Found {len(stages)} stages > {stages}")
    for stage in stages:
        stage_graph = nx.subgraph_view(
            graph,
            filter_node=lambda n: (graph.nodes.data(stage_attr)[n] <= stage)
        )
        logger.debug(f"Stage {stage}: Progress is a {stage_graph}")
        components = nx.weakly_connected_components(stage_graph)
        for component, component_nodes in enumerate(components):
            logger.debug(f"\tStage {stage} - Component {component} > {component_nodes}")
            components_dict[stage].append(component)
            for component_node in component_nodes:
                comp_dict = graph.nodes[component_node].get('component', {})
                comp_dict[stage] = component
                graph.nodes[component_node]['component'] = comp_dict

    return components_dict


def get_component(graph, stage, component):
    node_filter = lambda node: graph.nodes[node]['component'].get(stage, None) == component
    return nx.subgraph_view(graph, filter_node=node_filter)


def extract_stages(assembly, stages):
    con = nx.subgraph_view(
        assembly,
        filter_edge=lambda e1, e2: assembly[e1][e2]["EDGE_TYPE"] == "CONN",
    ).copy()

    stages_dict = {}
    for stage, stage_conn_nodes in enumerate(stages):
        logger.debug(f"\t Stage {stage} > {stage_conn_nodes}")

        assembly_sub_graph = _get_dep_graph_from_connections(con, stage_conn_nodes)
        for node in assembly_sub_graph.nodes:
            con.nodes[node]['stage'] = min(con.nodes.data('stage', default=stage)[node], stage)

        components_graph = nx.subgraph_view(
            con,
            filter_node=lambda n: (con.nodes.data('stage', default=stage)[n] < stage) or (n in assembly_sub_graph)
        )

        stages_dict[stage] = {}

        connected_components = nx.weakly_connected_components(components_graph)
        for component, connected_component in enumerate(connected_components):
            component_graph = assembly_sub_graph.subgraph(connected_component)
            if not component_graph:
                continue
            logger.debug(f"\t\tComponent: {component_graph} > {component_graph.nodes}")
            stages_dict[stage][component] = {}
            comp_conns = [n for n in component_graph if assembly_sub_graph.nodes[n]["TYPE"] == "CONN"]
            comp_parts = [n for n in component_graph if assembly_sub_graph.nodes[n]["TYPE"] == "PART"]
            comp_added = [p for p in comp_parts if con.nodes.data("stage")[p] == stage]

            stages_dict[stage][component]["conns"] = comp_conns
            stages_dict[stage][component]["parts"] = comp_parts
            stages_dict[stage][component]["added"] = comp_added
            stages_dict[stage][component]["group"] = [c for c in connected_component if
                                                            con.nodes.data("TYPE")[c] == "PART"]
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
