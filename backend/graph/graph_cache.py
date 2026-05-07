import hashlib
import json
import threading
from rdflib import Graph

_cache: dict[str, Graph] = {}
_lock = threading.Lock()


def _make_key(source_config: dict) -> str:
    """Return a stable SHA-256 hex digest for *source_config*."""
    canonical = json.dumps(source_config, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def get(source_config: dict) -> Graph | None:
    """
    Return the cached Graph for *source_config*, or None if not cached.
    """
    key = _make_key(source_config)
    with _lock:
        return _cache.get(key)


def store(source_config: dict, graph: Graph) -> None:
    """
    Store *graph* in the cache under *source_config*.

    If an entry already exists (race between two threads loading the
    same source), the existing entry is kept and the new graph is
    discarded.
    """
    key = _make_key(source_config)
    with _lock:
        if key not in _cache:
            _cache[key] = graph


def get_or_load(source_config: dict, loader_fn) -> Graph:
    """
    Return the cached graph, or call *loader_fn* to produce it and
    store the result.

    Used by the Ontology Extractor, which needs a graph but should
    not duplicate the loading logic of the data sources.

    Parameters
    ----------
    source_config : dict
    loader_fn : callable
        Zero-argument callable that returns an rdflib.Graph.
        Called only on cache miss.
    """
    cached = get(source_config)
    if cached is not None:
        return cached

    graph = loader_fn()
    store(source_config, graph)
    return graph


def invalidate(source_config: dict) -> bool:
    """
    Remove *source_config* from the cache.

    Returns True if an entry was removed, False if nothing was cached.
    """
    key = _make_key(source_config)
    with _lock:
        if key in _cache:
            del _cache[key]
            return True
        return False


def clear() -> None:
    """Evict all cached graphs (useful for testing)."""
    with _lock:
        _cache.clear()