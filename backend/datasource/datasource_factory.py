"""
datasource/datasource_factory.py
--------------------------------
Selection of the loading strategy for a source configuration.

Dispatches on the type field of a source configuration and returns the
matching DataSource implementation. Adding a new source type means
adding a strategy class and one case here — no other component changes.
"""

from datasource.datasource_exceptions import UnsupportedDataSourceException
from datasource.sources.rdf_file import RDFFileSource
from datasource.sources.sparql_endpoint import SPARQLEndpointSource

class DataSourceFactory:
    """
    Factory that maps a source configuration to its DataSource strategy.
    """

    @staticmethod
    def create(source_config: dict):
        """
        Instantiates the appropriate source reading strategy
        """

        source_type = source_config.get("type")

        match source_type:
            case "rdf_file":
                return RDFFileSource(
                file_path=source_config.get("file_path"),
                rdf_format=source_config.get("format")
            )
            case "sparql_endpoint":
                return SPARQLEndpointSource(
                endpoint_url=source_config.get("endpoint_url"),
                query=source_config.get("query")
            )
            case _:
                raise UnsupportedDataSourceException(
                f"Unsupported data source type: {source_type}"
            )

