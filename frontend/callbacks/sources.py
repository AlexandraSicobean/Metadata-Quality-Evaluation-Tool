import uuid

from dash import Input, Output, State, ALL, callback, ctx, no_update
import dash_bootstrap_components as dbc
from dash import html

from api_client import get_metrics, APIError
from layout.sidebar import build_source_item
from store import make_source


# ── 1. Populate metric accordion on startup ───────────────────────────────

_LABEL_STYLE = {
    "display": "flex", "alignItems": "center", "gap": "8px",
    "marginBottom": "4px", "fontSize": "0.875rem", "cursor": "pointer",
}

@callback(
    Output("metric-accordion",   "children"),
    Output("metric-selection",   "data"),
    Output("store-metric-dims",  "data"),
    Input("store-sources", "id"),   # fires once on load (id never changes)
)
def populate_metrics(_):
    """
    Fetches metrics from GET /metrics and:
      - Builds one accordion item per quality dimension (Intrinsic, Contextual…)
        each containing a checklist of its metrics, all selected by default.
      - Writes the flat list of all metric_ids to metric-selection.
      - Writes {metric_id: dimension} to store-metric-dims so the metric
        card grouping can use it without re-fetching from the backend.
    """
    try:
        metrics = get_metrics()
    except APIError:
        return [], [], {}

    from collections import OrderedDict
    by_dim: dict[str, list] = OrderedDict()
    for m in metrics:
        dim = m.get("dimension", "Other")
        by_dim.setdefault(dim, []).append(m)

    items = []
    for dim, dim_metrics in by_dim.items():
        options = [
            {"label": m["name"], "value": m["metric_id"],
             "title": m.get("description", "")}
            for m in dim_metrics
        ]
        values = []   # unchecked by default — user selects
        items.append(
            dbc.AccordionItem(
                dbc.Checklist(
                    id={"type": "dim-checklist", "index": dim},
                    options=options,
                    value=values,
                    labelStyle=_LABEL_STYLE,
                ),
                title=html.Span(
                    dim,
                    style={"fontSize": "0.82rem", "fontWeight": "500"},
                ),
            )
        )

    accordion = dbc.Accordion(
        items,
        start_collapsed=False,
        flush=True,
        className="mb-1",
        style={"fontSize": "0.875rem"},
    )

    dims_map = {m["metric_id"]: m.get("dimension", "Other") for m in metrics}
    return accordion, [], dims_map


# ── 1b. Sync flat metric-selection from all dim-checklists ────────────────

@callback(
    Output("metric-selection", "data", allow_duplicate=True),
    Input({"type": "dim-checklist", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def sync_metric_selection(checklist_values):
    """Flatten all per-dimension selections into one list."""
    flat = []
    for vals in (checklist_values or []):
        flat.extend(vals or [])
    return flat


# ── 2. Open modal (add OR edit) + close on Cancel ─────────────────────────
#
# We combine open-for-add, open-for-edit, and cancel into one callback
# because they all write to the same set of modal outputs.
# ctx.triggered_id tells us which button fired.

@callback(
    Output("modal-add-source",     "is_open"),
    Output("modal-title",          "children"),
    Output("modal-edit-id",        "data"),
    Output("input-source-label",   "value"),
    Output("input-source-type",    "value"),
    Output("input-file-path",      "value"),
    Output("input-file-format",    "value"),
    Output("input-endpoint-url",   "value"),
    Output("input-sparql-query",   "value"),
    Output("modal-source-feedback","children"),
    # Triggers
    Input("btn-add-source",   "n_clicks"),
    Input("btn-modal-cancel", "n_clicks"),
    Input({"type": "btn-edit-source", "index": ALL}, "n_clicks"),
    # State needed for edit pre-fill
    State("store-sources", "data"),
    prevent_initial_call=True,
)
def open_or_close_modal(
    _add, _cancel, _edit_clicks,
    sources,
):
    trigger = ctx.triggered_id

    # ── Cancel → just close, clear feedback ───────────────────────────────
    if trigger == "btn-modal-cancel":
        return (
            False,
            no_update, no_update, no_update, no_update,
            no_update, no_update, no_update, no_update,
            "",
        )

    # ── Add → open with blank fields ──────────────────────────────────────
    if trigger == "btn-add-source":
        return (
            True,
            "Add Data Source",
            None,          # no source being edited
            "",            # label
            "rdf_file",    # type
            "",            # file path
            "turtle",      # format
            "",            # endpoint url
            "",            # sparql query
            "",            # feedback
        )

    # ── Edit → open with pre-filled fields ────────────────────────────────
    if isinstance(trigger, dict) and trigger.get("type") == "btn-edit-source":
        # Guard: only act when a click actually happened
        if not any(n for n in (_edit_clicks or []) if n):
            return (False, no_update, no_update, no_update, no_update,
                    no_update, no_update, no_update, no_update, "")

        source_id = trigger["index"]
        source    = next((s for s in (sources or []) if s["id"] == source_id), None)

        if source is None:
            return (False, no_update, no_update, no_update, no_update,
                    no_update, no_update, no_update, no_update, "")

        cfg = source["source_config"]
        return (
            True,
            "Edit Data Source",
            source_id,
            source["label"],
            cfg["type"],
            cfg.get("file_path",     ""),
            cfg.get("format",        "turtle"),
            cfg.get("endpoint_url",  ""),
            cfg.get("query",         ""),
            "",
        )

    return (False, no_update, no_update, no_update, no_update,
            no_update, no_update, no_update, no_update, "")


# ── 3. Show / hide RDF vs SPARQL fields ───────────────────────────────────

@callback(
    Output("source-fields-rdf",    "style"),
    Output("source-fields-sparql", "style"),
    Input("input-source-type", "value"),
)
def toggle_source_fields(source_type):
    if source_type == "rdf_file":
        return {}, {"display": "none"}
    return {"display": "none"}, {}


# ── 4. Confirm: add new source OR update existing ─────────────────────────

@callback(
    Output("store-sources",         "data",     allow_duplicate=True),
    Output("modal-source-feedback", "children", allow_duplicate=True),
    Output("modal-add-source",      "is_open",  allow_duplicate=True),
    Input("btn-modal-confirm", "n_clicks"),
    State("modal-edit-id",       "data"),
    State("store-sources",       "data"),
    State("input-source-label",  "value"),
    State("input-source-type",   "value"),
    State("input-file-path",     "value"),
    State("input-file-format",   "value"),
    State("input-endpoint-url",  "value"),
    State("input-sparql-query",  "value"),
    prevent_initial_call=True,
)
def confirm_modal(
    n_clicks,
    edit_id,
    sources,
    label, source_type,
    file_path, file_format,
    endpoint_url, sparql_query,
):
    if not n_clicks:
        return no_update, no_update, no_update

    # ── Validate ──────────────────────────────────────────────────────────
    label = (label or "").strip()
    if not label:
        return no_update, "Please enter a label.", no_update

    if source_type == "rdf_file":
        file_path = (file_path or "").strip()
        if not file_path:
            return no_update, "Please enter a file path.", no_update
        source_config = {
            "type":      "rdf_file",
            "file_path": file_path,
            "format":    file_format or "turtle",
        }
    else:
        endpoint_url = (endpoint_url or "").strip()
        sparql_query = (sparql_query or "").strip()
        if not endpoint_url:
            return no_update, "Please enter an endpoint URL.", no_update
        if not sparql_query:
            return no_update, "Please enter a CONSTRUCT query.", no_update
        source_config = {
            "type":         "sparql_endpoint",
            "endpoint_url": endpoint_url,
            "query":        sparql_query,
        }

    sources = sources or []

    # ── Edit: update existing entry ───────────────────────────────────────
    if edit_id is not None:
        updated = []
        for s in sources:
            if s["id"] == edit_id:
                updated.append({
                    **s,
                    "label":         label,
                    "source_config": source_config,
                })
            else:
                updated.append(s)
        return updated, "", False

    # ── Add: append new entry ─────────────────────────────────────────────
    new_source = make_source(
        id=str(uuid.uuid4()),
        label=label,
        source_config=source_config,
        selected=True,
    )
    return sources + [new_source], "", False


# ── 5. Delete a source ────────────────────────────────────────────────────

@callback(
    Output("store-sources", "data", allow_duplicate=True),
    Input({"type": "btn-delete-source", "index": ALL}, "n_clicks"),
    State("store-sources", "data"),
    prevent_initial_call=True,
)
def delete_source(n_clicks_list, sources):
    if not any(n for n in (n_clicks_list or []) if n):
        return no_update

    source_id = ctx.triggered_id["index"]
    return [s for s in (sources or []) if s["id"] != source_id]


# ── 6. Toggle source selection via checkbox ───────────────────────────────

@callback(
    Output("store-sources", "data", allow_duplicate=True),
    Input({"type": "source-checkbox", "index": ALL}, "value"),
    State("store-sources", "data"),
    prevent_initial_call=True,
)
def toggle_source_selection(checkbox_values, sources):
    if not sources:
        return no_update

    checked_map = {
        item["id"]["index"]: item["value"]
        for item in ctx.inputs_list[0]
    }

    updated = []
    for source in sources:
        s = dict(source)
        if source["id"] in checked_map:
            s["selected"] = bool(checked_map[source["id"]])
        updated.append(s)

    return updated


# ── 7. Re-render the source list ──────────────────────────────────────────

@callback(
    Output("source-list", "children"),
    Input("store-sources", "data"),
)
def render_source_list(sources):
    if not sources:
        return html.P(
            "No sources added yet.",
            className="text-muted",
            style={"fontSize": "0.8rem"},
        )
    return [build_source_item(s) for s in sources]


# ── 8. Enable/disable Run button + set label ─────────────────────────────

@callback(
    Output("btn-run-evaluation", "disabled"),
    Output("btn-run-evaluation", "children"),
    Output("run-feedback",       "children"),
    Input("store-sources",    "data"),
    Input("metric-selection", "data"),
)
def update_run_button(sources, selected_metrics):
    selected_sources = [s for s in (sources or []) if s.get("selected")]
    n_sources = len(selected_sources)
    n_metrics = len(selected_metrics or [])

    if n_sources == 0 and n_metrics == 0:
        return True, "Run Evaluation", ""
    if n_sources == 0:
        return True, "Run Evaluation", "Select at least one data source."
    if n_metrics == 0:
        return True, "Run Evaluation", "Select at least one metric."

    label = "Run Analysis" if n_sources == 1 else "Run Comparison"
    return False, label, ""