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
                # print(dependency)
                deps.append((connection, dependency[6:]))

        dep = con.copy()
        dep.add_edges_from(deps, EDGE_TYPE="COLL", color='red')

    return con, dep
