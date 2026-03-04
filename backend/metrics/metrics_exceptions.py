class MetricError(Exception):
    """Generic error for metric errors"""
    pass


class MetricConfigurationError(MetricError):
    """Error for invalid metric configurations"""
    pass


class MetricExecutionError(MetricError):
    """Error for failed evaluation execution"""
    pass