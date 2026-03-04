class MetricResult:
    """
    The evaluation outcome of a single metric over
    a dataset

    Attributes
    ----------
    metric_id : str
        Unique identifier of the metric.

    name : str
        Human-readable metric name.

    score : float | None
        Computed metric score. None if evaluation failed.

    weight : float
        Weight used during score aggregation.

    status : str
        Execution status ("computed" or "error").

    details : dict
        Additional structured information about the evaluation.

    guidelines : dict
        Optional suggestions for improving dataset quality.
    """

    def __init__(
            self,
            metric_id: str,
            name: str,
            score: float,
            weight: float,
            status: str = "computed",
            details: dict | None = None,
            guidelines: dict | None = None
    ):
        self.metric_id = metric_id
        self.name = name
        self.score = score
        self.weight = weight
        self.status = status
        self.details = details
        self.guidelines = guidelines