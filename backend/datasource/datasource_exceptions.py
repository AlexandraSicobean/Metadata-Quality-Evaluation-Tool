"""
datasource/datasource_exceptions.py
-----------------------------------
Exception hierarchy for the data source layer.

All exceptions derive from DataSourceException, so a caller that does
not care which stage failed can catch the base class alone.
"""


class DataSourceException(Exception):
    """Generic exception for datasource errors."""
    pass

class UnsupportedDataSourceException(DataSourceException):
    """Exception for unsupported datasource types"""
    pass

class InvalidDataSourceConfiguration(DataSourceException):
    """Exception for invalid configurations of datasources"""
    pass

class DataSourceLoadError(DataSourceException):
    """Exception for failed loading of the datasource"""
    pass