import networkx as nx


def graph_from_gh_csv(csv_path):
    con = nx.DiGraph()
    deps = []
    with open(csv_path, 'r') as file:
        print(file.readline())
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
    for i in graph.nodes:
        graph.nodes[i]["TYPE"] = "PART" if graph[i].get('shape', None) == 'box' else "CONN"
    for s, e in graph.edges:
        graph[s][e]["EDGE_TYPE"] = "CONN" if graph[s][e].get('color', None) == 'red' else "COLL"

    return graph
