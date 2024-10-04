import logging
import networkx as nx


logger = logging.getLogger(__name__)

def graph_from_gh_csv(csv_path):
    con = nx.DiGraph()
    deps = []
    with open(csv_path, 'r') as file:
        logger.info(file.readline())
        for line in file:
            connection, part1, part2, dependency = line.strip().split(',')
            # print(connection, part1, part2, dependency)

            con.add_nodes_from([part1[6:], part2[6:]], TYPE="PART", color='black')
            con.add_node(connection, TYPE="CONN", style='filled', fontcolor='#FFFFFF', fillcolor='black')

            con.add_edges_from([
                (part1[6:], connection),
                (part2[6:], connection)
            ], EDGE_TYPE="CONN", color='grey')

            if dependency != r'<null>':
                deps.append((connection, dependency[6:]))
                con.add_edge(connection, dependency[6:], EDGE_TYPE='COLL', color='red')

    return con

def graph_from_assembly(connections, collisions):
    pass

def graph_from_dot_file(file_path):
    graph = nx.DiGraph(nx.nx_agraph.read_dot(file_path))
    shapes = graph.nodes.data('shape', default=None)
    for i in graph:
        graph.nodes[i]["TYPE"] = "PART" if shapes[i] == 'box' else "CONN"
        logger.debug(f"NODE: {i} > TYPE: {graph.nodes[i]['TYPE']}")
    colors = graph.edges.data('color', default=None)
    for s, e, c in colors:
        graph[s][e]["EDGE_TYPE"] = "COLL" if c == 'red' else "CONN"

    return graph
