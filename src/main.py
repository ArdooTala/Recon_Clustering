import networkx as nx
from recongraph.io_utils import file_writer, graph_generator
from recongraph.processors import graph_parser, graph_solver
from recongraph.processors.graph_parser import extract_stages
from recongraph.visualizer import graph_visualizer
from pathlib import Path
import logging

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    export_path = Path("../exports/")
    if not export_path.exists():
        export_path.mkdir()

    def viz_and_save(graph, path: Path, pos=None, bbox=None):
        file_writer.pygraphviz_export(graph, path.with_suffix(".pdf"))

        if not pos or not bbox:
            # pos, bbox = graph_visualizer.multipartite_layout_by_connections(graph)
            pos, bbox = graph_visualizer.pygraphviz_layout(graph)
        file_writer.inkscape_export(graph, path.with_suffix(".svg"), pos, bbox)
        # graph_visualizer.viz_dag(graph, pos)

    # assembly = graph_generator.graph_from_gh_csv("../assemblies/ReconSlab_Top-Connectivity.csv")
    # from assemblies.example_graph import con as assembly
    # assembly = graph_generator.graph_from_dot_file("../assemblies/simple.dot")
    assembly = nx.read_gml("../assemblies/exception.gml")
    # assembly = nx.read_gml("../assemblies/extended.gml")
    viz_and_save(assembly, export_path / "01-dep.pdf")

    resolved = graph_solver.resolve_dependencies(assembly)
    viz_and_save(resolved, export_path / "RESOLVED.pdf")
    stages = graph_parser.generate_stages_v2(resolved)
    stages_dict = graph_parser.extract_stages(assembly, stages)
    file_writer.export_stages(stages_dict, export_path / "export-components.csv" )
    print(assembly)
    print(resolved)
    exit()
    res_dep = graph_solver.direct_cluster_sccs(assembly.copy())
    viz_and_save(res_dep, export_path / "02-res_dep.pdf")

    file_writer.export_clusters(res_dep.graph['clusters_dict'], export_path / "export-clusters.csv")

    res_dep_xpn = graph_solver.expand_clusters(res_dep)
    viz_and_save(res_dep_xpn, export_path / "03-res_dep_xpn.pdf")

    stages = graph_parser.generate_stages_v2(res_dep_xpn)
    stages_dict = graph_parser.extract_stages(assembly, stages)
    file_writer.export_stages(stages_dict, export_path / "export-components.csv" )

    # res_con = graph_solver.convert_ass_dep_to_con_dep(res_dep_xpn)
    # viz_and_save(res_con, export_path / "04-res_con.pdf")

    # final_con = graph_solver.convert_ass_dep_to_con_dep(res_dep)
    # viz_and_save(final_con, export_path / "03-res_clustered.pdf")

    # final_xpn = graph_solver.replace_clusters_with_conns(final_con)
    # viz_and_save(final_xpn, export_path / "04-res_expanded.pdf")

    # stages_dict = graph_parser.generate_stages(assembly, res_con)

    # stages_graph = graph_solver.generate_stages_graph(res_con, stages_dict)
    # viz_and_save(stages_graph, export_path / "06-stages_dep.pdf")


    # gantt_dict = graph_parser.generate_gantt(res_con)
    # file_writer.export_gantt(gantt_dict, export_path / "export-stage_gantt.csv")

    print("FIN")
