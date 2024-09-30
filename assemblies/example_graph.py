import networkx as nx


con = nx.DiGraph()
con.add_edges_from([
    (1, 'A'),
    (3, 'A'),
    (1, 'B'),
    (4, 'B'),
    (2, 'C'),
    (5, 'C'),
    (2, 'D'),
    (6, 'D'),
    (0, 'E'),
    (1, 'E'),
    (0, 'F'),
    (2, 'F'),
    (6, 'G'),
    (7, 'G'),
    (0, 'H'),
    (7, 'H'),
    (5, 'I'),
    (8, 'I'),
], EDGE_TYPE='CONN')

for i in range(9):
    con.nodes[i]["TYPE"] = "PART"

for i in "ABCDEFGHI":
    con.nodes[i]["TYPE"] = "CONN"

con.add_edges_from([
    ('A', 2),
    ('B', 2),
    ('C', 1),
    ('D', 1),
    ('G', 5),
    ('I', 6)
], EDGE_TYPE="COLL")
