import networkx as nx
import xml.etree.ElementTree as ET
import pathlib


def export_graph_viz(g, name):
    # nx.nx_agraph.to_agraph(g).draw(f"exports/{name}.pdf", prog="neato",
    #                                args="-Gdiredgeconstraints=true -Gmode='ipsep' -Goverlap='prism5000'")
    nx.nx_agraph.to_agraph(g).draw(f"../exports/{name}.pdf", prog="dot",
                                   args="-Grankdir='LR' -Granksep=1.5 -Gsplines='false'")


def export_stages(stages_dict):
    print(stages_dict)
    with open("../exports/export-components.csv", 'w') as file:
        for stg in stages_dict.keys():
            for cmp in stages_dict[stg]:
                comp = stages_dict[stg][cmp]
                file.write(
                    f"{stg:02},{cmp:02},{';'.join(comp['conns'])},{';'.join(comp['parts'])},{';'.join(comp['added'])},{';'.join(comp['group'])}\n")


def export_gantt(gantt_dict):
    with open("../exports/export-stage_gantt.csv", 'w') as file:
        for el in gantt_dict.items():
            file.write(
                f"{el[0]},{el[1]['start']},{el[1]['end']},{el[1]['latest']},{';'.join(el[1]['deps'])},{';'.join(el[1]['children'])}\n")


def export_clusters(clusters_dict):
    with open("../exports/export-clusters.csv", 'w') as file:
        for lay in clusters_dict.items():
            for clst in lay[1]:
                file.write(f"{lay[0]},{clst[0]},{';'.join(clst[1])},{';'.join(clst[2])},{';'.join(clst[3])}\n")


def export_graph_to_inkscape(g, name):
    G = nx.nx_agraph.to_agraph(g)
    G.layout(prog="dot", args="-Grankdir='TB' -Granksep=0.5 -Gsplines='false' -Gnodesep=0.02 -Goutputorder='edgesfirst'")

    ET.register_namespace('', "http://www.w3.org/2000/svg")
    ET.register_namespace('inkscape', "http://www.inkscape.org/namespaces/inkscape")
    ET.register_namespace('sodipodi', "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")

    tree = ET.parse(pathlib.Path(__file__).parent / 'inkscape_template.svg')
    root = tree.getroot()

    radius = 10
    nodes_layer = root.findall(".//*[@id='nodes_1']")[0]
    for node in G.nodes():
        pos = G.get_node(node).attr["pos"].split(',')
        print(G.get_node(node).attr.to_dict())
        radius = 20 if G.get_node(node).attr["TYPE"] == 'CLUS' else 10

        node_group = ET.SubElement(nodes_layer, 'g')
        node_group.attrib['id'] = f'node_group_{node}'
        node_shape = ET.SubElement(node_group, 'circle', {
            'style': f"fill:#000000;stroke-width:0.264583",
            'id': f"shape_{node}",
            'cx': pos[0],
            'cy': pos[1],
            'r': f"{radius}"
        })
        node_text = ET.SubElement(node_group, 'text', {
            'xml:space': "preserve",
            'style': "font-size:4.0px;text-align:center;text-anchor:middle;fill:#eeffff;stroke:none",
            'x': f"{pos[0]}",
            'y': f"{pos[1]}",
            'id': f"label1_{node}"
        })
        node_text = ET.SubElement(node_text, 'tspan', {
            'sodipodi:role': "line",
            'id': f"label2_{node}",
            'style': "stroke-width:0.264583;stroke:none",
            'x': f"{pos[0]}",
            'y': f"{pos[1]}"
        })
        node_text.text = node

    edges_layer = root.findall(".//*[@id='edges_1']")[0]
    for edge in G.edges():
        edge_path = ET.SubElement(edges_layer, 'path', {
            "style": "fill:none;fill-rule:evenodd;stroke:#000000;stroke-width:0.264583px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1",
            "d": "m 71.642728,91.17392 25.709589,9.63346",
            "id": "{edge[0] + '__' + edge[1]}",
            "inkscape:connector-type": "polyline",
            "inkscape:connector-curvature": "0",
            "inkscape:connection-start": f"#shape_{edge[0]}",
            "inkscape:connection-end": f"#shape_{edge[1]}"
        })

    tree.write(f"../exports/{name}.svg")