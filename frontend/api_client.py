import requests

BACKEND_URL = "http://127.0.0.1:8000"

class APIError(Exception):
    """
    Raised when the backend returns an error or is unreachable.
    Carries a human-readable message suitable for display in the UI.
    """
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message     = message
        self.status_code = status_code


def get_metrics() -> list[dict]:
    """
    Fetches the list of available metrics from the backend.

    Called once on sidebar initialisation so the metric checklist
    always reflects what the backend actually supports.

    Returns
    -------
    list[dict]
        Each dict has: metric_id, name, description, dimension, weight.

    Raises
    ------
    APIError
        If the backend is unreachable or returns a non-200 response.
    """
    try:
        response = requests.get(f"{BACKEND_URL}/metrics", timeout=10)
    except requests.ConnectionError:
        raise APIError(
            "Cannot reach the backend. "
            "Make sure the FastAPI server is running on port 8000."
        )
    except requests.Timeout:
        raise APIError("Request to /metrics timed out.")

    if response.status_code != 200:
        raise APIError(
            f"Unexpected response from /metrics: {response.status_code}",
            status_code=response.status_code
        )

    return response.json()


def run_evaluation(sources: list[dict], metric_ids: list[str]) -> list[dict]:
    """
    Sends an evaluation request to POST /evaluate and returns the
    raw datasets list from the response.

    Parameters
    ----------
    sources
        Selected entries from store-sources. Each must have
        'dataset_id', 'label', and 'source_config'.
    metric_ids
        List of metric_id strings the user has selected.

    Returns
    -------
    list[dict]
        The raw 'datasets' array from the API response.

    Raises
    ------
    APIError
        If the backend is unreachable, returns a non-200 response,
        or returns a 400 (bad request, e.g. unknown metric).
    """
    payload = _build_evaluation_payload(sources, metric_ids)

    try:
        response = requests.post(
            f"{BACKEND_URL}/evaluate",
            json=payload,
            timeout=120       
        )
    except requests.ConnectionError:
        raise APIError(
            "Cannot reach the backend. "
            "Make sure the FastAPI server is running on port 8000."
        )
    except requests.Timeout:
        raise APIError(
            "The evaluation timed out. "
            "Try reducing the dataset size or the number of metrics."
        )

    if response.status_code == 400:
        detail = response.json().get("detail", "Bad request.")
        raise APIError(f"Evaluation request rejected: {detail}", status_code=400)

    if response.status_code != 200:
        raise APIError(
            f"Unexpected response from /evaluate: {response.status_code}",
            status_code=response.status_code
        )

    return response.json()["datasets"]


def _build_evaluation_payload(
    sources: list[dict],
    metric_ids: list[str]
) -> dict:
    """
    Translates store-sources entries and selected metric ids into
    the exact JSON shape that POST /evaluate expects.

    This is a private helper — only api_client should call it.
    Keeping the payload construction here means that if the API
    request shape ever changes, this is the only place to update.

    Parameters
    ----------
    sources
        Selected entries from store-sources.
    metric_ids
        Metric ids the user has selected.

    Returns
    -------
    dict
        Ready-to-serialise request body.
    """
    return {
        "datasets": [
            {
                "dataset_id":    source["id"],
                "label":         source["label"],
                "source_config": source["source_config"],
            }
            for source in sources
        ],
        "metrics": [
            {"metric_id": metric_id}
            for metric_id in metric_ids
        ]
    }