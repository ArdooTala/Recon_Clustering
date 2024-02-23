import networkx as nx
import tempfile
import matplotlib.pyplot as plt


def viz_g(g):
    subax1 = plt.subplot()
    nx.draw_circular(g, with_labels=True, font_weight='bold')
    plt.show()


def viz_agraph(g):
    ext = "png"
    suffix = f".{ext}"
    path = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)

    g.draw(path=path, prog='dot')
    path.close()

    plt.axis('off')
    plt.imshow(plt.imread(path.name))

    return path.name