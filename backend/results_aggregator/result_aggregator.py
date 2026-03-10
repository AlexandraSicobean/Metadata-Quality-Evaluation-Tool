from models.metric_result import MetricResult

class ResultAggregator:
    """
    Aggregates metric results into a final dataset score
    """

    def aggregate(self, metric_results: list[MetricResult]) -> float | None:
        """
        Computes the weighted score for a dataset

        Parameters
        ----------
        metric_results
            A list of metric results for each selected subdimension

        Returns
        -------
        result: float
            The normalized sum of all weighted metrics
        """

        total_weight = 0
        weighted_sum = 0

        for result in metric_results:

            if result.score is None:
                continue

            weighted_sum += result.score * result.weight
            total_weight += result.weight

            if total_weight == 0:
                return None
            
            return weighted_sum / total_weight


