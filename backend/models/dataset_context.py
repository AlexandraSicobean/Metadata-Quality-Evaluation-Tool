"""
models/dataset_context.py
-------------------------
The dataset as a metric sees it during evaluation.

The engine builds one context per dataset and passes it to every metric,
which keeps metric implementations free of any knowledge about loading,
caching, or scope filtering.

Both the scoped graph and the unfiltered one are carried, so a metric can
compute against the user's selection while still consulting the full
graph where that is genuinely needed.
"""


class DatasetContext:
    """
    Class representing a dataset during evaluation.
    Properties:
    - dataset identifier
    - dataset label
    - RDF graph loaded from the data source
    - scope
    """
    def __init__(self, dataset_id, label, graph, scope=None, full_graph=None):
        self.dataset_id = dataset_id
        self.label = label
        self.graph = graph          
        self.scope = scope
        self.full_graph = full_graph or graph