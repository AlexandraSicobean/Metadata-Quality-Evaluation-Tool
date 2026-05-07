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