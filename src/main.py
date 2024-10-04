from recongraph.io_utils import file_writer, graph_generator
from recongraph.processors import graph_parser, graph_solver
from recongraph.visualizer import graph_visualizer
from pathlib import Path

if __name__ == "__main__":
    export_path = Path("../exports/")
    if not export_path.exists():
        export_path.mkdir()

    def viz_and_save(graph, path: Path):
        file_writer.pygraphviz_export(graph, path.with_suffix(".pdf"))
        pos = graph_visualizer.multipartite_layout_by_connections(graph)
        file_writer.inkscape_export(graph, path.with_suffix(".svg"), pos)
        graph_visualizer.viz_dag(graph, pos)

    # con = graph_generator.graph_from_gh_csv("../assemblies/ReconSlab_Top-Connectivity.csv")
    # from assemblies.example_graph import con
    con = graph_generator.graph_from_dot_file("../assemblies/simple.dot")
    viz_and_save(con, export_path / "01-dep.pdf")

    final_ass = graph_solver.direct_cluster_sccs(con.copy())
    viz_and_save(final_ass, export_path / "02-res_dep.pdf")

    final_con = graph_solver.convert_ass_dep_to_con_dep(final_ass)
    viz_and_save(final_con, export_path / "03-res_clustered.pdf")

    final_con = graph_solver.replace_cluster_with_conns(final_con)
    viz_and_save(final_con, export_path / "04-res_expanded.pdf")

    stages_dict = graph_parser.generate_stages(con, final_con)
    # file_writer.export_stages(stages_dict, export_path / "export-components.csv" )

    stages_graph = graph_solver.generate_stages_graph(final_con, stages_dict)
    viz_and_save(stages_graph, export_path / "06-stages_dep.pdf")

    file_writer.export_clusters(graph_solver.clusters_dict, export_path / "export-clusters.csv")

    # gantt_dict = graph_parser.generate_gantt(final_con)
    # file_writer.export_gantt(gantt_dict, export_path / "export-stage_gantt.csv")

    print("FIN")
