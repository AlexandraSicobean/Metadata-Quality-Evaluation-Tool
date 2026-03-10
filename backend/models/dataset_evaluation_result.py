class DatasetEvaluationResult:
    """
    Aggregated evaluation result for a dataset
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