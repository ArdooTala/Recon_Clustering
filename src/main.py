import networkx as nx
from recongraph.io_utils import file_writer, graph_generator
from recongraph.processors import graph_parser, graph_solver
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

    # Load Assembly
    # assembly = graph_generator.graph_from_gh_csv("../assemblies/ReconSlab_Top-Connectivity.csv")
    assembly = graph_generator.graph_from_dot_file("../assemblies/simple.dot")
    # assembly = nx.read_gml("../assemblies/exception2.gml")
    # assembly = nx.read_gml("../assemblies/extended.gml")

    viz_and_save(assembly, export_path / "01-dep.pdf")

    resolved = graph_solver.resolve_dependencies(assembly)
    viz_and_save(resolved, export_path / "RESOLVED.pdf")

    # EARLY STAGES
    stages = graph_parser.add_stages(resolved)
    stages_dict = graph_parser.extract_stages(assembly, stages)
    file_writer.export_stages(stages_dict, export_path / "export-early_components.csv")

    # LATE STAGES
    stages = graph_parser.add_stages(resolved, earliest=False)
    stages_dict = graph_parser.extract_stages(assembly, stages)
    file_writer.export_stages(stages_dict, export_path / "export-late_components.csv")

    print("FIN")
