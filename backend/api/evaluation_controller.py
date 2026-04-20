from fastapi import APIRouter, HTTPException

from engine.evaluation_engine import EvaluationEngine

from models.request import EvaluationRequest
from models.response import (
    EvaluationResponse,
    DatasetEvaluationResponse,
    MetricResultResponse,
    MetricConfigResponse
)

from config.config_loader import load_metrics_config
from metrics.metric_registry import METRIC_REGISTRY

router = APIRouter()
engine = EvaluationEngine()

@router.get("/metrics", response_model=list[MetricConfigResponse])
def get_metrics():
    """
    Returns the list of available metrics as defined in metrics_config.json.
    Used by the frontend to populate the metric selection checklist.
    The frontend never hardcodes metric names — it always reads from here,
    so adding a new metric to the config automatically surfaces in the UI.
    """
    metric_config = load_metrics_config()
    return [
        MetricConfigResponse(
            metric_id=metric_id,
            name=config["name"],
            description=config["description"],
            dimension=config["dimension"],
            weight=config["weight"]
        )
        for metric_id, config in metric_config.items()
    ]

@router.post("/evaluate", response_model = EvaluationResponse)
def evaluate(request: EvaluationRequest):
    """
    Executes metadata quality evaluation for the requested datasets.

    The endpoint receives dataset descriptors and metric selections,
    initializes the metric plugins, runs the evaluation engine, and 
    converts results into API response models

    Parameters
    ----------
    request
        Evaluation request containing dataset definitions and
        selected metrics (TODO: add scope)

    Returns
    -------
    evaluation_response
        Structured evaluation results for all datasets

    Raises
    ------
    HTTPException
        If a requested metric is not defined in the configuration or
        no plugin implementation is registered for the metric.
    """

    metric_config = load_metrics_config()
    metrics = []

    for metric in request.metrics:
        metric_id = metric.metric_id

        if metric_id not in metric_config:
            raise HTTPException(
                status_code = 400,
                detail = f"Metric '{metric_id}' is not defined in configuration."
            )
        
        metric_class = METRIC_REGISTRY.get(metric_id)

        if not metric_class:
            raise HTTPException(
                status_code = 500,
                detail = f"No plugin registered for metric '{metric_id}'."
            )
        
        metrics.append(metric_class())

    datasets = [dataset.model_dump() for dataset in request.datasets]

    results = engine.evaluate(
        datasets=datasets,
        metrics=metrics
    )

    response_datasets = []

    for dataset_result in results:

        metric_responses = []

        for metric in dataset_result.metrics:

            metric_responses.append(
                MetricResultResponse(
                    metric_id=metric.metric_id,
                    name=metric.name,
                    score=metric.score,
                    weight=metric.weight,
                    status=metric.status,
                    details=metric.details
                )
            )

        response_datasets.append(
            DatasetEvaluationResponse(
                dataset_id=dataset_result.dataset_id,
                label=dataset_result.label,
                overall_score=dataset_result.overall_score,
                metrics=metric_responses
            )
        )

    return EvaluationResponse(datasets=response_datasets)
