from recongraph.io_utils import graph_parser, file_writer, graph_visualizer
from recongraph.graph_solver import graph_solver
from pathlib import Path

if __name__ == "__main__":
    export_path = Path("../exports/")
    if not export_path.exists():
        export_path.mkdir()

    # con = graph_generator.graph_from_gh_csv("../assemblies/ReconSlab_Top-Connectivity.csv")
    from assemblies import example_graph as eg
    con = eg.con
    file_writer.export_graph_viz(con, export_path / "01-dep.pdf")
    file_writer.export_graph_to_inkscape(con, export_path / "01-dep.svg")
    graph_visualizer.viz_dag(con)

    final_ass = graph_solver.direct_cluster_sccs(con.copy())
    file_writer.export_graph_viz(final_ass, export_path / "02-res_dep.pdf")
    file_writer.export_graph_to_inkscape(final_ass, export_path / "02-res_dep.svg")
    graph_visualizer.viz_dag(final_ass)

    final_con = graph_solver.convert_ass_dep_to_con_dep(final_ass)
    file_writer.export_graph_viz(final_con, export_path / "03-res_clustered.pdf")
    file_writer.export_graph_to_inkscape(final_con, export_path / "03-res_clustered.svg")
    graph_visualizer.viz_dag(final_con)

    final_con = graph_solver.replace_cluster_with_conns(final_con)
    file_writer.export_graph_viz(final_con, export_path / "04-res_expanded.pdf")
    file_writer.export_graph_to_inkscape(final_con, export_path / "04-res_expanded.svg")
    graph_visualizer.viz_dag(final_con)

    stages_dict = graph_parser.generate_stages(con, final_con)
    # file_writer.export_stages(stages_dict, export_path / "export-components.csv" )

    stages_graph = graph_solver.generate_stages_graph(final_con, stages_dict)
    file_writer.export_graph_viz(stages_graph, export_path / "06-stages_dep.pdf")
    file_writer.export_graph_to_inkscape(final_con, export_path / "06-stages_dep.svg")

    file_writer.export_clusters(graph_solver.clusters_dict, export_path / "export-clusters.csv")

    # gantt_dict = graph_parser.generate_gantt(final_con)
    # file_writer.export_gantt(gantt_dict, export_path / "export-stage_gantt.csv")

    print("FIN")
