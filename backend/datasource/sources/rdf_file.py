from pathlib import Path
from rdflib import Graph
from rdflib.plugin import PluginException

from datasource.datasource_interface import DataSource
from datasource.datasource_exceptions import (
    InvalidDataSourceConfiguration,
    DataSourceLoadError
)

class RDFFileSource(DataSource):
    """ 
    DataSource strategy that loads RDF data from a local file and stores it
    into an rdflib.Graph.
    """
    def __init__(self, file_path: str, rdf_format: str | None = None):
        """
        Parameters
        ----------
        file_path: str
            Path to the RDF file on the disk
        rdf_format: str
            Optional RDF serialization format (e.g., 'xml', 'turtle', 'nt'). 
            If None, rdflib attempts auto-detection
        
        Raises
        ------
        InvalidDataSourceConfiguration
            If the file path is missing
        InvalidDataSourceConfiguration
            If the file does not exist
        """

        if not file_path:
            raise InvalidDataSourceConfiguration("File path is missing.")
        
        self.file_path = Path(file_path)
        self.rdf_format = rdf_format

        if not self.file_path.exists():
            raise InvalidDataSourceConfiguration(f"File does not exist: {self.file_path}")
        
    def load(self) -> Graph:
        """
        Loads and parses the RDF file into an rdflib.Graph.

        Returns
        -------
        graph
            Graph containing all triples from the file
        
        Raises
        ------
        DataSourceLoadError
            If parsing fails or format is unsupported
        """
        graph = Graph()

        try:
            graph.parse(str(self.file_path), format = self.rdf_format)
        except PluginException as e:
            raise DataSourceLoadError(f"Unsupported RDF format: {self.rdf_format}") from e
        except Exception as e:
            raise DataSourceLoadError(f"Failed to parse the RDF file: {self.file_path}") from e
        
        return graph
        