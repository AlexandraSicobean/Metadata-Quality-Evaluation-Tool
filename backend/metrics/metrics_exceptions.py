class MetricError(Exception):
    """Base class for all metric evaluation errors."""
    pass


class MetricConfigurationError(MetricError):
    """
    Raised when a metric is misconfigured.
    Examples: missing or unparseable shape profile file.
    """
    pass


class MetricExecutionError(MetricError):
    """
    Raised when metric evaluation fails at runtime.
    Examples: SHACL validation engine error, unexpected graph structure.
    """
    pass


class ShapeProfileNotFoundError(MetricConfigurationError):
    """
    Raised when the expected SHACL shape profile file
    does not exist at the configured path.
    """
    pass


class EmptyGraphError(MetricExecutionError):
    """
    Raised when the RDF graph contains no triples,
    making evaluation impossible.
    """
    pass


class NoTargetRecordsError(MetricExecutionError):
    """
    Raised when the graph contains triples but no records
    match the targeting strategy of the selected shape profile.
    """
    pass


class ProfileDetectionError(MetricExecutionError):
    """
    Raised when schema profile detection fails due to
    an unexpected error during graph inspection.
    """
    pass