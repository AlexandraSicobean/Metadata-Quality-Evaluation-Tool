from pydantic import BaseModel
from typing import Optional, List

class MetricResultResponse(BaseModel):
    """
    API response model representing a single metric result.

    Attributes
    ----------
    metric_id : str
        Identifier of the metric.
    name : str
        Human-readable metric name.
    score : float | None
        Computed metric score.
    weight : float
        Weight used during score aggregation.
    status : str
        Metric execution status.
    details : dict | None
        Optional dictionary containing metric-specific details.
    """

    metric_id: str
    name: str
    score: float | None
    weight: float
    status: str
    details: dict | None

    @staticmethod
    def from_domain(metric):
        return MetricResultResponse(
            metric_id=metric.metric_id,
            name=metric.name,
            score=metric.score,
            weight=metric.weight,
            status=metric.status,
            details=metric.details
        )
    
class DatasetEvaluationResponse(BaseModel):
    """
    API response model for dataset evaluation results.

    Attributes
    ----------
    dataset_id : str
        Identifier of the evaluated dataset.
    label : str | None
        Human-readable dataset label.
    overall_score : float | None
        Aggregated score computed from all metrics.
    metrics : List[MetricResultResponse]
        List of metric results for the dataset.
    """

    dataset_id: str
    label: Optional[str]
    overall_score: Optional[float]
    metrics: List[MetricResultResponse]

class EvaluationResponse(BaseModel):
    """
    API response containing evaluation results for all datasets.

    Attributes
    ----------
    datasets : List[DatasetEvaluationResponse]
        Evaluation results for each dataset.
    """

    datasets: List[DatasetEvaluationResponse]

class MetricConfigResponse(BaseModel):
    """
    API response for the metrics list

    Attributes
    ----------
    metric_id : str
        Identifier of the metric
    name : str
        Name of the metric
    description : str
        Metric description.
    dimension : str
        Corresponding dimension
    weight: float
        Weight in the aggregated evaluation
    """
    metric_id:   str
    name:        str
    description: str
    dimension:   str
    weight:      float