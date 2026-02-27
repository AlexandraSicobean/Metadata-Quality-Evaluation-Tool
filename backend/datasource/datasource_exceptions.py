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