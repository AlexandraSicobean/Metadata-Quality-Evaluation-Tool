"""
datasource/sources/sparql_endpoint.py
-------------------------------------
DataSource strategy for remote SPARQL endpoints.

Executes a CONSTRUCT query through RDFLib's SPARQLStore and materialises
the result into an rdflib.Graph. CONSTRUCT is required rather than
optional: a SELECT query returns bindings, not a graph, and is rejected
as a load error.

Queries sent in JSON request bodies must be on a single line — embedded
newlines cause several public endpoints, Wikidata and DBpedia among
them, to answer with 502 or 422. YAML configuration files avoid this
because the folded block scalar collapses the query automatically.

As with local files, the retrieved graph is stored in the shared cache
so repeated evaluations do not re-query the endpoint.
"""

from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLStore

from datasource.datasource_interface import DataSource
from datasource.datasource_exceptions import (
    InvalidDataSourceConfiguration,
    DataSourceLoadError
)
import graph.graph_cache as _cache


class SPARQLEndpointSource(DataSource):
    """
    DataSource strategy that retrieves RDF data from a SPARQL endpoint
    using a CONSTRUCT query and materializes it into an rdflib.Graph.
    """

    def __init__(self, endpoint_url: str, query: str):
        """
        Parameters
        ----------
        endpoint_url : str
            Public SPARQL endpoint URL.
        query : str
            SPARQL CONSTRUCT query.

        Raises
        ------
        InvalidDataSourceConfiguration
            If the endpoint or query is missing.
        """
        if not endpoint_url:
            raise InvalidDataSourceConfiguration("Endpoint is missing.")
        if not query:
            raise InvalidDataSourceConfiguration("Query is missing.")

        self.endpoint_url = endpoint_url
        self.query = query
        self._source_config = {
            "type": "sparql_endpoint",
            "endpoint_url": endpoint_url,
            "query": query,
        }

    def load(self) -> Graph:
        """
        Returns the queried RDF graph, fetching from the endpoint on
        first call and from cache on subsequent calls.

        Returns
        -------
        rdflib.Graph

        Raises
        ------
        DataSourceLoadError
            If the endpoint cannot be reached or the query fails.
        """
        cached = _cache.get(self._source_config)
        if cached is not None:
            return cached

        try:
            store = SPARQLStore(
                self.endpoint_url,
                headers={
                    "User-Agent": "MetadataQualityTool/1.0",
                    "Accept": "text/turtle, application/rdf+xml"
                }
            )
            graph = Graph(store=store)
            results = graph.query(self.query)

            if not hasattr(results, "graph"):
                raise DataSourceLoadError(
                    "SPARQL query could not return a CONSTRUCT graph."
                )

            loaded_graph = results.graph

        except DataSourceLoadError:
            raise
        except Exception as e:
            raise DataSourceLoadError(
                f"Failed to query SPARQL endpoint: {self.endpoint_url}"
            ) from e

        _cache.store(self._source_config, loaded_graph)
        return loaded_graph