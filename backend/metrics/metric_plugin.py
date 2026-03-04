from abc import ABC, abstractmethod
from models.dataset_context import DatasetContext
from models.metric_result import MetricResult

class MetricPlugin(ABC):
    """
    Abstract base class for all metadata quality metrics

    Each metric receives a DatasetContext object and
    returns a MetricResult describing the evaluation 
    outcome.

    Subclasses must implement the 'evaluate' method
    """
    id : str
    name: str
    description: str
    dimension: str
    subdimension: str
    weight: float = 1.0

    @abstractmethod
    def evaluate(self, context: DatasetContext) -> MetricResult:
        """
        Evaluate the metric on the provided dataset

        Parameters
        ----------
        context : DatasetContext
            Object containing dataset metadata and 
            the RDF graph to be evaluated.

        Returns
        -------
        MetricResult
            Structured evaluation result.
        """
        pass

    def error_result(self, message: str) -> MetricResult:
        """
        Create a standardized MetricResult to present a 
        failed metric evaluation.

        Parameters
        ----------
        message : str
            Human-readable description of the error that occurred during
            metric execution.

        Returns
        -------
        MetricResult
            Metric result object with status set to "error" and the error
            message stored in the details field.
        """
        return MetricResult(
            metric_id=self.id,
            name=self.name,
            score=None,
            weight=self.weight,
            status="error",
            details={"error": message}
        )