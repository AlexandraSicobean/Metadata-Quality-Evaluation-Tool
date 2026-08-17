"""
metrics/plugins/connectivity.py
--------------------------------
Measures whether URIs referenced by the dataset are dereferenceable
over HTTP.

Every distinct URI appearing anywhere in the graph — as a subject, a
predicate, or an object — is checked, once, over the network. There is
no sampling: a broken vocabulary term (predicate) is treated as no less
significant than a broken data URI (subject/object), and checking is
kept tractable through concurrency rather than by checking fewer URIs.

Check strategy
---------------
Each URI is first screened with a cheap local syntax check, then with a
scheme check: only http/https URIs are actually dereferenceable over
the web, so anything else (file:, urn:, mailto:, an unbound CURIE
prefix that parses as a bogus "scheme", etc.) is scored as a failure
without ever being sent over the network — sending it would either be
meaningless or just trip a library-level "unsupported scheme" error.
Checking is done concurrently via asyncio/httpx rather than threads,
since the workload here (thousands of short, mostly-independent HTTP
round trips) is exactly what async I/O is suited for — a thread pool
tops out in the tens of concurrent requests before overhead dominates,
while this can comfortably hold hundreds open at once. A per-host
concurrency limit is enforced alongside the global one, since without
it, high overall concurrency just means hammering whichever single
domain the dataset happens to reuse most (very common in Linked Data)
and tripping its rate limiting — which would show up as false failures
that have nothing to do with real connectivity.

Syntactically valid http(s) URIs are checked with HEAD first, falling
back to GET when a server rejects or mishandles HEAD (405/501, or any
request exception). Redirects — including the 303-see-other pattern
that is standard practice for real-world objects in Linked Data — are
followed automatically and do not count as failures on their own; only
a redirect loop does.

Score
-----
    1 - (unreachable_count / total_distinct_uris)

A graph with no URIs at all (e.g. entirely blank nodes and literals)
scores 1.0 with details["not_applicable"] set, rather than being
treated as a failure.

4xx responses are split into three classification buckets rather than
one, since they carry very different evidentiary weight: NOT_FOUND
(404/410) plausibly means the resource really is gone; ACCESS_DENIED
(401/403) and RATE_LIMITED (429) usually mean the *server* blocked an
automated client rather than that the resource doesn't exist — the
same request often succeeds in a browser. This split does not change
the score (all three still count as unreachable — that's a separate,
deliberately unchanged decision), but when ACCESS_DENIED/RATE_LIMITED
make up a large share of the unreachable set, details["ambiguity_warning"]
is set so the frontend can tell the user the score may understate true
reachability.

Not implemented (v1)
---------------------
The taxonomy definition of Connectivity also covers endpoint
stability/responsiveness for datasets sourced from a SPARQL endpoint.
That is intentionally out of scope here: DatasetContext does not carry
the dataset's source type or endpoint URL, and adding that would mean
changing the Evaluation Engine's construction of DatasetContext — every
other metric so far has been addable as a standalone plugin file with
no changes elsewhere, and this metric preserves that property. A future
revision could extend DatasetContext with source metadata to support
an endpoint-responsiveness sub-score.

Export
------
The complete (uncapped) list of unreachable URIs is stored in the
export cache during evaluate(). The frontend receives only a capped
sample (MAX_SAMPLES) for display. The full list is available via
GET /export/{dataset_id}/connectivity/unreachable_uris.
"""

import asyncio
import re
from collections import defaultdict
from urllib.parse import urlparse

import httpx
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from metrics.metric_plugin import MetricPlugin
from models.dataset_context import DatasetContext
from models.metric_result import MetricResult
from metrics.metrics_exceptions import EmptyGraphError
from export import export_cache

METRIC_ID = "connectivity"

EXPORT_CATEGORIES = ["unreachable_uris"]

# Display-only cap on the "samples" list returned to the frontend. Does
# NOT limit which URIs get checked — every distinct URI is always
# checked; this only limits how many unreachable ones are echoed back
# in the response instead of only in the export cache.
MAX_SAMPLES = 50

USER_AGENT = "MetadataQualityTool/1.0"
REQUEST_TIMEOUT = 3.0

# Every distinct URI is checked, with no sampling — concurrency is the
# only lever for keeping that tractable on large or SPARQL-sourced
# datasets with thousands of distinct URIs. MAX_CONCURRENCY bounds how
# many requests are in flight at once overall; MAX_PER_HOST bounds how
# many of those may target the same host at once, so exhaustive
# checking doesn't look like a burst attack against whichever domain
# the dataset happens to reuse the most.
MAX_CONCURRENCY = 200
MAX_PER_HOST    = 8

_HTTP_SCHEMES = {"http", "https"}

# Classification buckets, shared by scoring, export, and the frontend charts.
OK                = "ok"
REDIRECT_LOOP     = "redirect_loop"
NOT_FOUND         = "not_found"        # 404, 410 — plausibly a genuinely gone resource
ACCESS_DENIED     = "access_denied"    # 401, 403 — often a bot block, not a dead resource
RATE_LIMITED      = "rate_limited"     # 429 — server-side throttling, not evidence either way
CLIENT_ERROR      = "client_error"     # any other 4xx
SERVER_ERROR      = "server_error"
TIMEOUT           = "timeout"
CONNECTION_ERROR  = "connection_error"
DNS_ERROR         = "dns_error"
INVALID_URI       = "invalid_uri"
NON_HTTP_SCHEME   = "non_http_scheme"

# classification buckets whose 4xx status is more likely to reflect the
# server blocking an automated client than the resource actually being
# gone — used only to compute the ambiguity warning, never the score.
_AMBIGUOUS_CLASSIFICATIONS = {ACCESS_DENIED, RATE_LIMITED}

# Share of the unreachable set that has to be ACCESS_DENIED/RATE_LIMITED
# before we tell the user the score may be understating true reachability.
AMBIGUITY_WARNING_THRESHOLD = 0.3

_DNS_ERROR_MARKERS = (
    "getaddrinfo failed",
    "name or service not known",
    "nodename nor servname provided",
    "name resolution",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_uri(uri: str) -> bool:
    """
    Cheap syntactic pre-filter used to skip URIs that cannot possibly
    resolve, without spending a network request on them.

    Parameters
    ----------
    uri : str
        The URI string to check.

    Returns
    -------
    bool
    """
    if not uri or not uri.strip() or " " in uri:
        return False
    try:
        parsed = urlparse(uri)
    except Exception:
        return False
    if not parsed.scheme:
        return False
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*$", parsed.scheme))


def _classify_client_error(status: int) -> str:
    """
    Map a 4xx status code to a classification bucket.

    Split out because a 404/410 carries different weight than a
    401/403/429 — the latter two are common responses to *any*
    automated client regardless of whether the resource exists, while
    a 404/410 is a more direct signal that it doesn't.

    Parameters
    ----------
    status : int
        The HTTP status code, expected to be in [400, 500).

    Returns
    -------
    str
        One of NOT_FOUND, ACCESS_DENIED, RATE_LIMITED, or CLIENT_ERROR.
    """
    if status in (404, 410):
        return NOT_FOUND
    if status in (401, 403):
        return ACCESS_DENIED
    if status == 429:
        return RATE_LIMITED
    return CLIENT_ERROR


def _classify_exception(exc: Exception) -> str:
    """
    Map an httpx exception (or any other unexpected exception raised
    while attempting a check) to one of the classification buckets.

    Parameters
    ----------
    exc : Exception
        The exception raised by the request attempt.

    Returns
    -------
    str
        One of REDIRECT_LOOP, TIMEOUT, DNS_ERROR, or CONNECTION_ERROR.
    """
    if isinstance(exc, httpx.TooManyRedirects):
        return REDIRECT_LOOP
    if isinstance(exc, httpx.TimeoutException):
        return TIMEOUT
    if isinstance(exc, httpx.ConnectError):
        text = str(exc).lower()
        if any(marker in text for marker in _DNS_ERROR_MARKERS):
            return DNS_ERROR
        return CONNECTION_ERROR
    return CONNECTION_ERROR


async def _check_uri_async(
    uri: str,
    client: httpx.AsyncClient,
    global_sem: asyncio.Semaphore,
    host_sem: asyncio.Semaphore,
) -> dict:
    """
    Check whether a single URI is dereferenceable.

    Parameters
    ----------
    uri : str
        The URI to check.
    client : httpx.AsyncClient
        Shared client for connection pooling across concurrent checks.
    global_sem : asyncio.Semaphore
        Caps the total number of in-flight requests across all hosts.
    host_sem : asyncio.Semaphore
        Caps the number of in-flight requests to this URI's host.

    Returns
    -------
    dict
        Keys: uri, classification, status_code, reachable.
    """
    if not _is_valid_uri(uri):
        return {"uri": uri, "classification": INVALID_URI,
                "status_code": None, "reachable": False}

    scheme = urlparse(uri).scheme.lower()
    if scheme not in _HTTP_SCHEMES:
        # Not meaningless to check, but not checkable over HTTP — file:,
        # urn:, mailto:, or an unbound CURIE prefix that urlparse read as
        # a bogus scheme. Still counts as a connectivity failure (it's
        # not a working web identifier), but never worth a request.
        return {"uri": uri, "classification": NON_HTTP_SCHEME,
                "status_code": None, "reachable": False}

    headers = {"User-Agent": USER_AGENT}

    async def _get():
        return await client.get(uri, headers=headers, timeout=REQUEST_TIMEOUT,
                                 follow_redirects=True)

    # Everything below is wrapped in one broad except: a single malformed
    # or otherwise pathological URI must be scored as unreachable, not
    # allowed to crash the rest of the dataset's evaluation.
    async with global_sem, host_sem:
        try:
            try:
                resp = await client.head(uri, headers=headers, timeout=REQUEST_TIMEOUT,
                                          follow_redirects=True)
                if resp.status_code in (405, 501):
                    resp = await _get()
            except httpx.HTTPError:
                resp = await _get()

            status = resp.status_code
        except Exception as exc:
            return {"uri": uri, "classification": _classify_exception(exc),
                    "status_code": None, "reachable": False}

    if 200 <= status < 400:
        return {"uri": uri, "classification": OK,
                "status_code": status, "reachable": True}
    if 400 <= status < 500:
        return {"uri": uri, "classification": _classify_client_error(status),
                "status_code": status, "reachable": False}
    return {"uri": uri, "classification": SERVER_ERROR,
            "status_code": status, "reachable": False}


async def _check_all_async(uris: list[str]) -> list[dict]:
    """
    Check every URI concurrently via asyncio/httpx.

    A global semaphore bounds total in-flight requests; a per-host
    semaphore (one per distinct netloc, created lazily) additionally
    bounds how many of those may target the same host at once.

    Parameters
    ----------
    uris : list of str
        Distinct URIs to check. Every one is checked — no sampling.

    Returns
    -------
    list of dict
        One result dict per URI, as returned by _check_uri_async.
    """
    global_sem = asyncio.Semaphore(MAX_CONCURRENCY)
    host_semaphores: dict[str, asyncio.Semaphore] = {}

    def _host_sem(uri: str) -> asyncio.Semaphore:
        host = urlparse(uri).netloc
        sem = host_semaphores.get(host)
        if sem is None:
            sem = asyncio.Semaphore(MAX_PER_HOST)
            host_semaphores[host] = sem
        return sem

    limits = httpx.Limits(
        max_connections=MAX_CONCURRENCY,
        max_keepalive_connections=MAX_PER_HOST,
    )
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [
            _check_uri_async(uri, client, global_sem, _host_sem(uri))
            for uri in uris
        ]
        return await asyncio.gather(*tasks)


def _check_all(uris: list[str]) -> list[dict]:
    """
    Synchronous entry point for the rest of the plugin (and for
    evaluate(), which is called from a plain synchronous context).
    Runs the async batch check to completion in its own event loop.

    Parameters
    ----------
    uris : list of str
        Distinct URIs to check. Every one is checked — no sampling.

    Returns
    -------
    list of dict
        One result dict per URI, as returned by _check_uri_async.
    """
    return asyncio.run(_check_all_async(uris))


def _build_class_violation_rates(
    violating_subjects: set[str],
    types: dict[str, set],
) -> dict[str, float]:
    """
    Compute the proportion of resources in each class that are
    unreachable, at the resource level.

    Only URIs that are also subjects with an rdf:type triple contribute
    a row here — an unreachable URI that only ever appears as an object
    or predicate has no class to attribute it to.

    Parameters
    ----------
    violating_subjects : set of str
        URIs classified as unreachable.
    types : dict[str, set]
        Mapping of subject URI to the set of class URIs it belongs to.

    Returns
    -------
    dict[str, float]
        Mapping of class URI to violation rate (0.0 to 1.0).
    """
    class_totals: dict[str, int] = defaultdict(int)
    class_violations: dict[str, int] = defaultdict(int)

    for subject_uri, classes in types.items():
        for cls in classes:
            class_totals[cls] += 1
            if subject_uri in violating_subjects:
                class_violations[cls] += 1

    return {
        cls: round(class_violations[cls] / class_totals[cls], 4)
        for cls in class_totals
        if class_totals[cls] > 0
    }


def _collect(graph: Graph) -> dict:
    """
    Single pass over the graph collecting every distinct URI in any
    triple position, plus a subject_types map for the class
    violation-rate breakdown.

    Parameters
    ----------
    graph : rdflib.Graph
        The RDF graph to analyse.

    Returns
    -------
    dict with keys:
        uris           — set of every distinct URI string found
        subject_types  — {subject_uri: set of class URIs}
    """
    uris: set[str] = set()
    subject_types: dict[str, set] = defaultdict(set)

    for subject, predicate, obj in graph:
        if isinstance(subject, URIRef):
            uris.add(str(subject))
        # Predicates are always URIRefs in RDF — never blank nodes or literals.
        uris.add(str(predicate))
        if isinstance(obj, URIRef):
            uris.add(str(obj))

        if (predicate == RDF.type and isinstance(subject, URIRef)
                and isinstance(obj, URIRef)):
            subject_types[str(subject)].add(str(obj))

    return {"uris": uris, "subject_types": dict(subject_types)}


# ---------------------------------------------------------------------------
# Metric plugin
# ---------------------------------------------------------------------------

class ConnectivityMetric(MetricPlugin):
    """
    Scores the proportion of distinct URIs referenced by the dataset
    that are dereferenceable over HTTP, and exports the full list of
    unreachable ones.
    """

    id = METRIC_ID

    def evaluate(self, context: DatasetContext) -> MetricResult:
        """
        Evaluate connectivity of the dataset.

        Collects every distinct URI referenced anywhere in the graph
        and checks each one over HTTP, concurrently. There is no
        sampling — every run checks every URI found. URIs that fail a
        local syntax check are scored as failures without a network
        request being attempted.

        Parameters
        ----------
        context : DatasetContext
            Contains the RDF graph to evaluate and optional scope.

        Returns
        -------
        MetricResult
            Score: 1 - (unreachable_count / total_distinct_uris).
            Details: classification breakdown, per-class violation
            rates, and a capped sample of unreachable URIs for display.

        Raises
        ------
        EmptyGraphError
            If the dataset graph contains no triples.
        """
        graph         = context.graph
        dataset_id    = context.dataset_id
        dataset_label = context.label or context.dataset_id

        if len(graph) == 0:
            raise EmptyGraphError(
                f"Dataset '{dataset_id}' contains an empty graph."
            )

        raw   = _collect(graph)
        uris  = sorted(raw["uris"])
        types = raw["subject_types"]

        if not uris:
            return MetricResult(
                metric_id=self.id,
                name=self.name,
                score=1.0,
                weight=self.weight,
                status="computed",
                details={
                    "not_applicable":    True,
                    "total_checked":     0,
                    "unreachable_count": 0,
                    "by_classification": [],
                    "class_violation_rates": {},
                    "samples": [],
                },
            )

        results = _check_all(uris)
        unreachable = [r for r in results if not r["reachable"]]

        by_classification: dict[str, int] = defaultdict(int)
        for r in results:
            by_classification[r["classification"]] += 1

        score = round(1 - len(unreachable) / len(results), 4)

        violating = {r["uri"] for r in unreachable}
        class_violation_rates = _build_class_violation_rates(violating, types)

        ambiguous_count = sum(
            1 for r in unreachable
            if r["classification"] in _AMBIGUOUS_CLASSIFICATIONS
        )
        ambiguity_ratio = (
            ambiguous_count / len(unreachable) if unreachable else 0.0
        )

        export_rows = [
            {
                "dataset_label": dataset_label,
                "uri":            r["uri"],
                "classification": r["classification"],
                "status_code":    r["status_code"],
            }
            for r in unreachable
        ]
        export_cache.store(dataset_id, METRIC_ID, "unreachable_uris", export_rows)

        details = {
            "total_checked":     len(results),
            "unreachable_count": len(unreachable),
            "by_classification": [
                {"classification": c, "count": n}
                for c, n in sorted(by_classification.items(),
                                    key=lambda x: x[1], reverse=True)
            ],
            "class_violation_rates": class_violation_rates,
            "samples": [
                {
                    "uri":            r["uri"],
                    "classification": r["classification"],
                    "status_code":    r["status_code"],
                }
                for r in unreachable[:MAX_SAMPLES]
            ],
        }

        if ambiguity_ratio > AMBIGUITY_WARNING_THRESHOLD:
            details["ambiguity_warning"] = (
                f"{ambiguous_count} of {len(unreachable)} unreachable URIs were "
                "blocked (401/403) or rate-limited (429) rather than confirmed "
                "missing (404/410). Servers commonly return these to any "
                "automated tool regardless of whether the resource actually "
                "exists, so the true reachability of this dataset may be "
                "higher than the score above suggests."
            )

        return MetricResult(
            metric_id=self.id,
            name=self.name,
            score=score,
            weight=self.weight,
            status="computed",
            details=details,
            exports_available=EXPORT_CATEGORIES,
        )
