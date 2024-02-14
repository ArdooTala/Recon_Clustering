import networkx as nx


con = nx.DiGraph()
deps = []
with open("assemblies/ReconSlab_Top-Connectivity.csv", 'r') as file:
    print(file.readline())
    for line in file:
        connection, part1, part2, dependency = line.strip().split(',')
        # print(connection, part1, part2, dependency)

        con.add_nodes_from([part1, part2], TYPE="PART")
        con.add_node(connection, TYPE="CONN")

        con.add_edges_from([
            (part1, connection),
            (part2, connection)
        ])

        if dependency != r'<null>':
            # print(dependency)
            deps.append((connection, dependency))

    dep = con.copy()
    dep.add_edges_from(deps, collision_edge=True)
