from pydantic import BaseModel
from typing import Optional, List

class SourceConfig(BaseModel):
    """
    Configuration for loading datasets

    Attributes
    ----------
    type : str
        Type of data source (e.g., 'rdf_file', 'sparql_endpoint').
    file_path : str | None
        Path to a local RDF file.
    format : str | None
        RDF serialization format.
    endpoint_url : str | None
        SPARQL endpoint URL.
    query : str | None
        SPARQL query used to retrieve RDF data.
    """

    type: str
    file_path: Optional[str] = None
    format: Optional[str] = None
    endpoint_url: Optional[str] = None
    query: Optional[str] = None

class DatasetRequest(BaseModel):
    """
    Dataset descriptor received from the frontend.

    Attributes
    ----------
    dataset_id : str
        Unique dataset identifier.
    label : str | None
        Optional human-readable label.
    source_config : SourceConfig
        Configuration describing how the dataset should be loaded.
    """

    dataset_id: str
    label: Optional[str] = None
    source_config: SourceConfig

class MetricSelection(BaseModel):
    """
    Metric selection provided by the frontend.

    Attributes
    ----------
    metric_id : str
        Identifier of the metric to evaluate.
    enabled : bool
        Indicates whether the metric is enabled.
    """

    metric_id: str
    enabled: bool = True

class EvaluationRequest(BaseModel):
    """
    Evaluation request received by the API.

    Attributes
    ----------
    datasets : List[DatasetRequest]
        List of datasets to evaluate.
    metrics : List[MetricSelection]
        List of selected metrics.
    """

    datasets: List[DatasetRequest]
    metrics: List[MetricSelection]