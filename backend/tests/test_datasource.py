import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from rdflib import Graph

from datasource.datasource_factory import DataSourceFactory
from datasource.datasource_exceptions import (
    InvalidDataSourceConfiguration,
    DataSourceLoadError,
    UnsupportedDataSourceException,
)


TEST_RESOURCES = Path(__file__).parent / "resources"


# ------------------------------------------------------------------
# SUCCESS CASES
# ------------------------------------------------------------------

def test_rdf_file_valid_turtle():
    """Valid Turtle file should load successfully."""

    source_config = {
        "type": "rdf_file",
        "file_path": str(TEST_RESOURCES / "valid.ttl"),
        "format": "turtle",
    }

    source = DataSourceFactory.create(source_config)
    graph = source.load()

    assert len(graph) > 0


def test_rdf_file_autodetect_format():
    """Valid Turtle file should load without explicitly specifying format."""

    source_config = {
        "type": "rdf_file",
        "file_path": str(TEST_RESOURCES / "valid.ttl"),
        # No format provided
    }

    source = DataSourceFactory.create(source_config)
    graph = source.load()

    assert len(graph) > 0

def test_sparql_endpoint_valid_construct():
    """Valid SPARQL endpoint query should return a graph."""

    source_config = {
        "type": "sparql_endpoint",
        "endpoint_url": "http://fake-endpoint.org/sparql",
        "query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
    }

    fake_graph = Graph()
    fake_graph.add((
        fake_graph.namespace_manager.compute_qname("rdf:type")[1],
        fake_graph.namespace_manager.compute_qname("rdf:type")[1],
        fake_graph.namespace_manager.compute_qname("rdf:type")[1],
    ))

    mock_results = MagicMock()
    mock_results.graph = fake_graph

    with patch("datasource.sources.sparql_endpoint.Graph.query", return_value=mock_results):
        source = DataSourceFactory.create(source_config)
        graph = source.load()

        assert isinstance(graph, Graph)


# ------------------------------------------------------------------
# CONFIGURATION ERRORS (constructor-level)
# ------------------------------------------------------------------

def test_rdf_file_missing_path():
    """Missing file path should raise configuration error."""

    source_config = {
        "type": "rdf_file",
        "file_path": "",
        "format": "turtle",
    }

    with pytest.raises(InvalidDataSourceConfiguration):
        DataSourceFactory.create(source_config)


def test_rdf_file_nonexistent_file():
    """Non-existent file should raise configuration error."""

    source_config = {
        "type": "rdf_file",
        "file_path": str(TEST_RESOURCES / "does_not_exist.ttl"),
        "format": "turtle",
    }

    with pytest.raises(InvalidDataSourceConfiguration):
        DataSourceFactory.create(source_config)

def test_sparql_endpoint_missing_endpoint():
    """Not including an endpoint should draise an InvalidDataSourceConfiguration error"""

    source_config = {
        "type": "sparql_endpoint",
        "endpoint_url": "",
        "query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
    }

    with pytest.raises(InvalidDataSourceConfiguration):
        DataSourceFactory.create(source_config)

def test_sparql_endpoint_missing_query():
    """Not including a query should draise an InvalidDataSourceConfiguration error"""

    source_config = {
        "type": "sparql_endpoint",
        "endpoint_url": "http://fake-endpoint.org/sparql",
        "query": "",
    }

    with pytest.raises(InvalidDataSourceConfiguration):
        DataSourceFactory.create(source_config)
        
# ------------------------------------------------------------------
# PARSING ERRORS (load-level)
# ------------------------------------------------------------------

def test_rdf_file_invalid_format_declaration():
    """Declaring an invalid RDF format should raise DataSourceLoadError."""

    source_config = {
        "type": "rdf_file",
        "file_path": str(TEST_RESOURCES / "valid.ttl"),
        "format": "invalid_format",
    }

    source = DataSourceFactory.create(source_config)

    with pytest.raises(DataSourceLoadError):
        source.load()


def test_rdf_file_invalid_syntax():
    """Malformed RDF content should raise DataSourceLoadError."""

    source_config = {
        "type": "rdf_file",
        "file_path": str(TEST_RESOURCES / "invalid.ttl"),
        "format": "turtle",
    }

    source = DataSourceFactory.create(source_config)

    with pytest.raises(DataSourceLoadError):
        source.load()


# ------------------------------------------------------------------
# FACTORY ERRORS
# ------------------------------------------------------------------

def test_unsupported_datasource_type():
    """Unknown datasource type should raise UnsupportedDataSourceException."""
    
    source_config = {
        "type": "unknown_type",
        "file_path": "whatever",
    }

    with pytest.raises(UnsupportedDataSourceException):
        DataSourceFactory.create(source_config)