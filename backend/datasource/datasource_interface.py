from abc import ABC, abstractmethod
from rdflib import Graph

class DataSource(ABC):
    """Abstract strategy for loading RDF data from different sources."""

    @abstractmethod
    def load(self) -> Graph:
        """Loads the data and returns it as rdflib:Graph."""
        pass

