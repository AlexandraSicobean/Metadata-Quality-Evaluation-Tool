"""
datasource/datasource_interface.py
----------------------------------
The Strategy contract shared by all data sources.

Every source type — local file, remote endpoint, or any future
addition — implements the same single-method interface and returns an
rdflib.Graph. Callers therefore never branch on source type.
"""

from abc import ABC, abstractmethod
from rdflib import Graph

class DataSource(ABC):
    """Abstract strategy for loading RDF data from different sources."""

    @abstractmethod
    def load(self) -> Graph:
        """Loads the data and returns it as rdflib:Graph."""
        pass

