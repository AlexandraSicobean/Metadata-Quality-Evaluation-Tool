from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLStore

from datasource.datasource_interface import DataSource
from datasource.datasource_exceptions import (
    InvalidDataSourceConfiguration,
    DataSourceLoadError
)

class SPARQLEndpointSource(DataSource):
    """
    DataSource strategy that retrieves RDF data from a SPARQL endpoint
    using a CONSTRUCT query and materializes it into an rdflib.Graph.
    """

    def __init__(self, endpoint_url: str, query: str):
        """
        Parameters
        ----------
        endpoint_url: str
            Public endpoint url
        query: str
            SPARQL query 
        
        Raises
        ------
        InvalidDataSourceConfiguration
            If the endpoint or query is missing
        """

        if not endpoint_url:
            raise InvalidDataSourceConfiguration("Endpoint is missing")
        if not query:
            raise InvalidDataSourceConfiguration("Query is missing")
        
        self.endpoint_url = endpoint_url
        self.query = query

    def load(self) -> Graph:
        """
        Retrieves data that matches the query and stores it into
        an rdflib.Graph

        Returns
        -------
        graph
            Graph containing all triples matching the query
        
        Raises
        ------
        DataSourceLoadError
            If a CONSTRUCT query cannot be returned
        """
        try:
            store = SPARQLStore(self.endpoint_url)
            graph = Graph(store = store)
            results = graph.query(self.query)

            if not hasattr(results, "graph"):
                raise DataSourceLoadError(
                    "SPARQL query could not return a CONSTRUCT graph."
                )

            return results.graph
        
        except Exception as e:
            raise DataSourceLoadError(
                f"Failed to query SPARQL endpoint: {self.endpoint_url}"
            ) from e