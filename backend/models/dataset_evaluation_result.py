class DatasetEvaluationResult:
    """
    Aggregated evaluation result for a dataset.

    Attributes
    ----------
    dataset_id : str
        Unique identifier of the evaluated dataset.
    label : str | None
        Human-readable dataset label.
    overall_score : float | None
        Aggregated score computed from all evaluated metrics.
        May be None if no numeric metrics are available.
    metrics : list
        List of ``MetricResult`` objects for the dataset.
    stats : dict | None
        Basic graph statistics::
            {"triple_count": int, "entity_count": int, "class_count": int}

        None if stats were not computed.
    """

    def __init__(
        self,
        dataset_id: str,
        label: str | None,
        overall_score: float | None,
        metrics: list,
        stats: dict | None = None,
    ):
        self.dataset_id = dataset_id
        self.label = label
        self.overall_score = overall_score
        self.metrics = metrics
        self.stats = stats