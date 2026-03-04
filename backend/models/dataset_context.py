class DatasetContext:
    """
    Class representing a dataset during evaluation.
    Properties:
    - dataset identifier
    - dataset label
    - RDF graph loaded from the data source
    """
    def __init__(self, dataset_id: str, label: str, graph):
        self.dataset_id = dataset_id
        self.label = label
        self.graph = graph