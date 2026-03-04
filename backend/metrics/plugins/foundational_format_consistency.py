from pathlib import Path
from rdflib import Graph
from rdflib.namespace import RDF, SH
from pyshacl import validate

from metrics.metric_plugin import MetricPlugin
from metrics.metrics_exceptions import (
    MetricConfigurationError,
    MetricExecutionError
)

from models.dataset_context import DatasetContext
from models.metric_result import MetricResult
from config.config_loader import load_metrics_config


class FoundationalFormatConsistency(MetricPlugin):
    """
    Metric plugin that evaluates foundational format consistency.

    This metric evaluates RDF data against a set of SHACL shapes
    designed to detect representation problems such as:
    TODO: add responsibilities after writing the shape

    Validation is performed using the pySHACL engine
    """

    id = "foundational_format_consistency"
    
    def __init__(self):

        config = load_metrics_config().get(self.id)

        if not config:
            raise MetricConfigurationError(
                f"Missing configuration for metric '{self.id}'"
            )
        
        self.name = config.get("name")
        self.description = config.get("description")
        self.dimension = config.get("dimension")
        self.subdimension = config.get("subdimension")
        self.weight = config.get("weight", 1.0)

        shapes_path = config.get("shapes_file")

        if not shapes_path:
            raise MetricConfigurationError(
                f"Missing shapes_file in configuration for metric '{self.id}'"
            )

        self.shapes_file = Path(__file__).parents[1] / shapes_path
        
    
    def evaluate(self, context: DatasetContext) -> MetricResult:
        """
        Evaluate the foundational and format consistency 
        of the provided dataset

        Parameters
        ----------
        context : DatasetContext
            Object containing dataset metadata and 
            the RDF graph to be evaluated.

        Returns
        -------
        MetricResult
            Structured evaluation result.

        Raises
        ------
        MetricExecutionError
            For failure during evaluation 

        """
        data_graph = context.graph

        try:
            shapes_graph = Graph()
            shapes_graph.parse(str(self.shapes_file), format="turtle")
            conforms, report_graph, _ = validate(
                data_graph=data_graph,
                shacl_graph=shapes_graph,
                inference="rdfs",
                abort_on_first=False,
                allow_infos=True,
                allow_warnings=True
            )

            violations = list(report_graph.subjects(RDF.type, SH.ValidationResult))
            violation_count = len(violations)

            evaluated_nodes = len(data_graph)

            score = max(0, 1 - violation_count / evaluated_nodes) if evaluated_nodes else 1.0

            details = {
                "violations": violation_count,
                "evaluated_nodes": evaluated_nodes,
                "conforms": conforms
            }

            return MetricResult(
                metric_id=self.id,
                name=self.name,
                score=score,
                weight=self.weight,
                status="computed",
                details=details
            )

        except Exception as e:
            error = MetricExecutionError(
                f"Metric '{self.id}' failed for dataset '{context.dataset_id}': {str(e)}"
            )

            return MetricResult(
                metric_id=self.id,
                name=self.name,
                score=None,
                weight=self.weight,
                status="error",
                details={"error": str(e)}
            )