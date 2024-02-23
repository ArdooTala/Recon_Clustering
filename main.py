from io_utils import graph_generator, graph_parser, file_writer
from graph_solver import *


if __name__ == "__main__":
    con, dep = graph_generator.graph_from_gh_csv("assemblies/ReconSlab_Top-Connectivity.csv")
    file_writer.export_graph_viz(dep, "dep")

    final_ass = direct_cluster_sccs(con.copy(), dep.copy(), 0)
    file_writer.export_graph_viz(final_ass, "res_dep")

    final_con = convert_ass_dep_to_con_dep(final_ass)
    file_writer.export_graph_viz(final_con, "res_clustered")

    final_con = replace_cluster_with_conns(final_con)
    file_writer.export_graph_viz(final_con, "res_expanded")

    stages_dict = graph_parser.generate_stages(con, final_con)
    file_writer.export_stages(stages_dict)

    stages_graph = generate_stages_graph(final_con, stages_dict)
    file_writer.export_graph_viz(stages_graph, "stages_dep")

    file_writer.export_clusters(clusters_dict)

    gantt_dict = graph_parser.generate_gantt(final_con)
    file_writer.export_gantt(gantt_dict)

    nx.write_gexf(dep, f"exports/dep.gexf")

    print("FIN")
