"""
datasource/sources/rdf_file.py
------------------------------
DataSource strategy for local RDF files.

Parses a file from disk into an rdflib.Graph, inferring the
serialisation format from the file extension when none is given.
Results are stored in the shared graph cache, so repeated evaluations of
the same file pay the parsing cost only once.

RDFLib's own logger is silenced during parsing so that malformed input
surfaces as a DataSourceLoadError rather than as unstructured warnings
on the server console.
"""

from rdflib import Graph
import logging


from datasource.datasource_interface import DataSource
from datasource.datasource_exceptions import (
    InvalidDataSourceConfiguration,
    DataSourceLoadError
)
import graph.graph_cache as _cache

class RDFFileSource(DataSource):
    """
    DataSource strategy that loads RDF data from a local file.
    """

    def __init__(self, file_path: str, rdf_format: str = None):
        """
        Parameters
        ----------
        file_path : str
            Path to the local RDF file.
        rdf_format : str | None
            RDF serialisation format (e.g. 'turtle', 'xml', 'n3').
            If None, rdflib will attempt auto-detection.

        Raises
        ------
        InvalidDataSourceConfiguration
            If file_path is missing.
        """
        if not file_path:
            raise InvalidDataSourceConfiguration("File path is missing.")

        self.file_path = file_path
        self.rdf_format = rdf_format
        self._source_config = {
            "type": "rdf_file",
            "file_path": file_path,
            "format": rdf_format,
        }

    def load(self) -> Graph:
        """
        Returns the parsed RDF graph, loading from disk on first call
        and from cache on subsequent calls.

        Returns
        -------
        rdflib.Graph

        Raises
        ------
        DataSourceLoadError
            If the file cannot be found or parsed.
        """
        cached = _cache.get(self._source_config)
        if cached is not None:
            return cached

        try:
            graph = Graph()
            rdflib_logger = logging.getLogger("rdflib")
            previous_level = rdflib_logger.level
            rdflib_logger.setLevel(logging.CRITICAL)
            try:
                graph.parse(self.file_path, format=self.rdf_format)
            finally:
                rdflib_logger.setLevel(previous_level)
        except FileNotFoundError:
            raise DataSourceLoadError(
                f"RDF file not found: {self.file_path}"
            )
        except Exception as e:
            raise DataSourceLoadError(
                f"Failed to parse RDF file '{self.file_path}': {e}"
            ) from e

        _cache.store(self._source_config, graph)
        return graph