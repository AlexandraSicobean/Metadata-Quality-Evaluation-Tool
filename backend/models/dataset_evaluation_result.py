class DatasetEvaluationResult:
    """
    Aggregated evaluation result for a dataset

    Attributes
    ----------
    dataset_id : str
        Unique identifier of the evaluated dataset.
    label : str
        Human-readable dataset label.
    overall_score : float | None
        Aggregated score computed from all evaluated metrics.
        May be None if no numeric metrics are available.
    metrics : list
        List of metric evaluation results for the dataset.
    """

    def __init__(
            self,
            dataset_id: str,
            label: str,
            overall_score: float | None,
            metrics: list
    ):
        self.dataset_id = dataset_id
        self.label = label
        self.overall_score = overall_score
        self.metrics = metrics