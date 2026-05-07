# ── store-sources ──────────────────────────────────────────────────────────
#
# {
#   "id":           str   — client-generated uuid4
#   "label":        str
#   "selected":     bool
#   "expanded":     bool  — whether the ontology tree is shown in the sidebar
#   "source_config": {
#       "type":         "rdf_file" | "sparql_endpoint"
#       rdf_file:     "file_path", "format"
#       sparql:       "endpoint_url", "query"
#   }
#   "scope":        list[str] | None  — selected class URIs, None = full graph
# }

SOURCES_DEFAULT = []


def make_source(id, label, source_config, selected=False):
    return {
        "id":            id,
        "label":         label,
        "selected":      selected,
        "expanded":      False,
        "source_config": source_config,
        "scope":         None,
    }


# ── store-results ──────────────────────────────────────────────────────────

RESULTS_DEFAULT = None


def make_results(datasets, error_message=None):
    if error_message is not None:
        return {
            "status":        "error",
            "mode":          None,
            "error_message": error_message,
            "datasets":      [],
        }

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


# ── store-ontology ─────────────────────────────────────────────────────────
#
# Maps source_id → ontology tree returned by POST /ontology.
# Populated lazily when the user expands a source card.
#
# {
#   "<source_id>": {
#       "dataset_id": str,
#       "classes": [
#           {
#               "uri":            str,
#               "label":          str,
#               "instance_count": int,
#               "properties": [{"uri": str, "label": str, "count": int}],
#               "children":   [... recursive ...]
#           }
#       ]
#   }
# }

ONTOLOGY_DEFAULT = {}



UI_DEFAULT = {
    "active_metric": None,
    "active_class":  None,
}