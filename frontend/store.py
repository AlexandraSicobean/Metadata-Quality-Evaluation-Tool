# store.py
#
# Canonical definitions of the three dcc.Store data shapes.
# No Dash imports — this is plain Python used for documentation,
# default values, and validation helpers.
#
# Any module that reads from or writes to a store should import
# the relevant default or helper from here.


# ── store-sources ──────────────────────────────────────────────────────────
#
# A list of data source configurations the user has added.
# Each entry corresponds to one dataset the user can select for evaluation.
#
# {
#   "id":           str   — client-generated unique id (uuid4)
#   "label":        str   — human-readable name shown in the sidebar
#   "selected":     bool  — whether this source is checked for evaluation
#   "source_config": {
#       "type":         "rdf_file" | "sparql_endpoint"
#
#       rdf_file only:
#       "file_path":    str
#       "format":       str  e.g. "turtle", "xml", "n3"
#
#       sparql_endpoint only:
#       "endpoint_url": str
#       "query":        str  — CONSTRUCT query
#   }
# }

SOURCES_DEFAULT = []


def make_source(id, label, source_config, selected=False):
    """
    Constructor for a single store-sources entry.
    Use this everywhere instead of building the dict by hand,
    so that structural changes only need to happen here.
    """
    return {
        "id":            id,
        "label":         label,
        "selected":      selected,
        "source_config": source_config,
    }


# ── store-results ──────────────────────────────────────────────────────────
#
# The result of the last evaluation run, or None if not yet run.
#
# {
#   "status":        "ok" | "error"
#   "mode":          "analysis" | "comparison"
#   "error_message": str | None
#   "datasets":      list — raw datasets array from the API response
# }
#
# "mode" is derived from len(datasets):
#   1 dataset   → "analysis"
#   2+ datasets → "comparison"
#
# "status" is "error" if any metric on any dataset has status == "error".
# In that case "datasets" still holds the raw response for error inspection,
# but the UI will not render charts — it will show the error message instead.

RESULTS_DEFAULT = None


def make_results(datasets, error_message=None):
    """
    Builds the store-results dict from a raw API response datasets list.
    Detects errors and sets mode automatically.
    """
    if error_message is not None:
        return {
            "status":        "error",
            "mode":          None,
            "error_message": error_message,
            "datasets":      [],
        }

    # Check for any metric-level errors in the response
    for dataset in datasets:
        for metric in dataset.get("metrics", []):
            if metric.get("status") == "error":
                return {
                    "status":        "error",
                    "mode":          None,
                    "error_message": (
                        f"Metric '{metric['name']}' failed on dataset "
                        f"'{dataset['label']}': {metric.get('details', 'no details')}"
                    ),
                    "datasets":      datasets,
                }

    return {
        "status":        "ok",
        "mode":          "analysis" if len(datasets) == 1 else "comparison",
        "error_message": None,
        "datasets":      datasets,
    }


# ── store-ui ───────────────────────────────────────────────────────────────
#
# Lightweight UI interaction state that needs to survive across callbacks
# but is not business data.
#
# {
#   "active_metric": str | None  — metric_id of the currently expanded card
#   "active_class":  str | None  — URI of the selected class in property chart
# }

UI_DEFAULT = {
    "active_metric": None,
    "active_class":  None,
}