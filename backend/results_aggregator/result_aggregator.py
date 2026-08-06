"""
results_aggregator/result_aggregator.py
---------------------------------------
Aggregation of metric results into a single dataset score.

Only metrics that produced a numeric score contribute to the weighted
mean. Metrics that failed or were not applicable are excluded rather
than counted as zero, so a partially successful evaluation still yields
a meaningful score. A dataset with no usable metric returns None instead
of a fabricated number.
"""

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


