import importlib.util
import logging
from email.policy import default

import networkx as nx
import xml.etree.ElementTree as ET
import pathlib
import subprocess
import warnings


logger = logging.getLogger(__name__)
VIZ_DEP_INSTALLED = (importlib.util.find_spec('pygraphviz')) is not None

EDGE_COLORS = {
    "CONN": '#000000',
    "COLL": '#FF0000',
    "EXTR": '#00FF00',
}


def pygraphviz_export(g, name):
    if not VIZ_DEP_INSTALLED:
        warnings.warn("Package pygraphviz is not installed. Skipping visualization.")
        return
    # nx.nx_agraph.to_agraph(g).draw(f"exports/{name}.pdf", prog="neato",
    #                                args="-Gdiredgeconstraints=true -Gmode='ipsep' -Goverlap='prism5000'")
    nx.nx_agraph.to_agraph(g).draw(name, prog="dot",
                                   args="-Grankdir='LR' -Granksep=1.5 -Gsplines='false'")


def export_stages(stages_dict, name):
    logger.debug(stages_dict)
    with open(name, 'w') as file:
        file.write(
            f"Stage,component,connections,parts,newly_added,group\n")
        for stg in stages_dict.keys():
            for cmp in stages_dict[stg]:
                comp = stages_dict[stg][cmp]
                file.write(
                    f"{stg:02},{cmp:02},{';'.join(comp['conns'])},{';'.join(comp['parts'])},{';'.join(comp['added'])},{';'.join(comp['group'])}\n")


def export_gantt(gantt_dict, name):
    with open(name, 'w') as file:
        file.write(
            f"item,start,end,latest,deps,children\n")
        for el in gantt_dict.items():
            file.write(
                f"{el[0]},{el[1]['start']},{el[1]['end']},{el[1]['latest']},{';'.join(el[1]['deps'])},{';'.join(el[1]['children'])}\n")


def export_clusters(clusters_dict, name):
    with open(name, 'w') as file:
        file.write(f"Level,Name,Parts,Connections,SubClusters\n")
        for lay in clusters_dict.items():
            for clst in lay[1]:
                file.write(f"{lay[0]},{clst[0]},{';'.join(clst[1])},{';'.join(clst[2])},{';'.join(clst[3])}\n")


def inkscape_export(g, name, node_pos, bbox):
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    ET.register_namespace('inkscape', "http://www.inkscape.org/namespaces/inkscape")
    ET.register_namespace('sodipodi', "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")

    tree = ET.parse(pathlib.Path(__file__).parent / 'inkscape_template.svg')
    root = tree.getroot()
    root.set("viewBox", ','.join(map(str, bbox)))
    root.set("width", str(bbox[2]))
    root.set("height", str(bbox[3]))
    radius = 10
    nodes_layer = root.findall(".//*[@id='nodes_1']")[0]
    for node in g.nodes():
        pos = node_pos[node]

        rad = radius * 2 if g.nodes[node]["TYPE"] == 'CLUS' else radius

        node_group = ET.SubElement(nodes_layer, 'g')
        node_group.attrib['id'] = f'node_group_{node}'

        if g.nodes[node]["TYPE"] == 'PART':
            node_shape = ET.SubElement(node_group, 'rect', {
                "style": "fill:#000000;stroke-width:0.25",
                "id": f"shape_{node}",
                "width": f"{rad * 2}",
                "height": f"{rad * 2}",
                "x": f"{pos[0] - rad}",
                "y": f"{pos[1] - rad}",
            })
        else:
            node_shape = ET.SubElement(node_group, 'circle', {
                'style': f"fill:#000000;stroke-width:0.25",
                'id': f"shape_{node}",
                'cx': f"{pos[0]}",
                'cy': f"{pos[1]}",
                'r': f"{rad}"
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

    for edge in g.edges():
        stroke_color = EDGE_COLORS.get(g.edges[*edge].get("EDGE_TYPE", None), '#88FF88')
        # stroke_color = '#000000' if  g.edges[*edge].get("EDGE_TYPE", None) == 'CONN' else '#FF0000'
        edge_path = ET.SubElement(edges_layer, 'path', {
            "style": f"fill:none;fill-rule:evenodd;stroke:{stroke_color};stroke-width:0.264583px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1;marker-end:url(#RoundedArrow)",
            "d": "m 71.642728,91.17392 25.709589,9.63346",
            "id": "{edge[0] + '__' + edge[1]}",
            "inkscape:connector-type": "polyline",
            "inkscape:connector-curvature": "0",
            "inkscape:connection-start": f"#shape_{edge[0]}",
            "inkscape:connection-end": f"#shape_{edge[1]}"
        })

    subprocess.run(["inkscape", "--pipe", f"--export-filename={name}"], input=ET.tostring(root))
