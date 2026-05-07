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
    State("source-list",   "children"),
)
def render_source_list(sources, current_children):
    # Only rebuild the list when the set of source ids changes (add/delete)
    # or when label/source_config changes (edit).
    # Skip when only scope or expanded changed — those are handled by
    # render_scope_trees and update_scope callbacks respectively.
    # This prevents those callbacks from destroying the scope tree content.
    if not sources:
        return html.P(
            "No sources added yet.",
            className="text-muted",
            style={"fontSize": "0.8rem"},
        )

    if ctx.triggered_id == "store-sources" and current_children:
        # Extract current source ids and labels from the existing rendered list
        # to detect whether a structural change actually happened.
        # If only scope/expanded changed, return no_update.
        triggered_keys = [
            (s["id"], s["label"], s["source_config"].get("file_path", "")
             or s["source_config"].get("endpoint_url", ""))
            for s in sources
        ]
        # We can't easily inspect current_children (they're dicts), so instead
        # we store the last-rendered keys in a module-level variable.
        if triggered_keys == _last_rendered_source_keys[0]:
            return no_update
        _last_rendered_source_keys[0] = triggered_keys

    return [build_source_item(s) for s in sources]


# Module-level mutable container to track last rendered source keys.
# List wrapper used so it can be mutated inside the callback (closure).
_last_rendered_source_keys = [[]]


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


# ── 9. Toggle source expanded state + fetch ontology ─────────────────────
#
# Fires when the user clicks the expand (▸/▾) button on a source card.
# Toggles source["expanded"] in store-sources, then if expanding and the
# ontology hasn't been fetched yet, calls POST /ontology and stores the
# result in store-ontology keyed by source_id.

@callback(
    Output("store-sources",  "data", allow_duplicate=True),
    Output("store-ontology", "data", allow_duplicate=True),
    Input({"type": "btn-expand-source", "index": ALL}, "n_clicks"),
    State("store-sources",  "data"),
    State("store-ontology", "data"),
    prevent_initial_call=True,
)
def toggle_expand_source(n_clicks_list, sources, ontology_store):
    if not any(n for n in (n_clicks_list or []) if n):
        return no_update, no_update

    source_id = ctx.triggered_id["index"]
    sources   = list(sources or [])
    ontology  = dict(ontology_store or {})

    updated = []
    for s in sources:
        if s["id"] == source_id:
            s = dict(s)
            s["expanded"] = not s.get("expanded", False)

            if s["expanded"] and source_id not in ontology:
                # Write sentinel None first — triggers render_scope_trees
                # to show the spinner before the fetch starts.
                ontology[source_id] = None
        updated.append(s)

    return updated, ontology


@callback(
    Output("store-ontology", "data", allow_duplicate=True),
    Input("store-ontology",  "data"),
    State("store-sources",   "data"),
    prevent_initial_call=True,
)
def fetch_ontology(ontology_store, sources):
    """
    Fires after toggle_expand_source writes the None sentinel.
    Finds any source with a None entry in the ontology store,
    fetches the real data, and writes it back.
    Runs as a separate callback so the spinner has time to render first.
    """
    ontology = dict(ontology_store or {})
    sources  = sources or []

    # Find sources that need fetching (sentinel = None)
    to_fetch = [
        s for s in sources
        if s.get("expanded") and ontology.get(s["id"]) is None
    ]
    if not to_fetch:
        return no_update

    updated = False
    for s in to_fetch:
        sid = s["id"]
        try:
            from api_client import get_ontology, APIError
            result = get_ontology(s)
            ontology[sid] = result
        except APIError as exc:
            ontology[sid] = {"error": str(exc)}
        updated = True

    return ontology if updated else no_update


# ── 10. Render scope tree when source is expanded ─────────────────────────

@callback(
    Output({"type": "scope-tree", "index": ALL}, "children"),
    Output({"type": "scope-tree", "index": ALL}, "style"),
    Input("store-ontology", "data"),
    State("store-sources",  "data"),
    prevent_initial_call=True,
)
def render_scope_trees(ontology_store, sources):
    from layout.sidebar import build_scope_tree

    sources      = sources or []
    ontology     = ontology_store or {}
    children_out = []
    styles_out   = []

    base_style = {
        "border":          "1px solid #dee2e6",
        "borderTop":       "none",
        "borderRadius":    "0 0 4px 4px",
        "padding":         "8px",
        "backgroundColor": "#f8f9fa",
        "maxHeight":       "260px",
        "overflowY":       "auto",
    }

    for s in sources:
        sid      = s["id"]
        expanded = s.get("expanded", False)
        scope    = set(s.get("scope") or [])

        if not expanded:
            children_out.append(no_update)
            styles_out.append({"display": "none"})
            continue

        styles_out.append({**base_style, "display": "block"})

        tree_data = ontology.get(sid)
        if tree_data is None:
            # Fetch in progress — show a spinner via dbc.Spinner inline
            children_out.append(
                html.Div([
                    dbc.Spinner(size="sm", color="primary",
                                spinner_style={"marginRight": "8px"}),
                    html.Span("Loading ontology…",
                              className="text-muted",
                              style={"fontSize": "0.8rem"}),
                ], style={"display": "flex", "alignItems": "center",
                          "padding": "8px 0"})
            )
        elif "error" in tree_data:
            children_out.append(
                html.P(f"Could not load ontology: {tree_data['error']}",
                       className="text-danger mb-0",
                       style={"fontSize": "0.8rem"})
            )
        else:
            children_out.append(
                build_scope_tree(tree_data.get("classes", []), sid, scope)
            )

    return children_out, styles_out


# ── 11. Update scope in store-sources when a class checkbox is toggled ────
#
# Cascade rules:
#   Check parent   → add parent + all descendants
#   Uncheck parent → remove parent + all descendants
#   Uncheck child  → remove only that child (parent stays checked)

def _all_descendants(uri: str, classes: list) -> set:
    """Recursively collect all descendant URIs of a given class URI."""
    result = set()
    for cls in classes:
        if cls["uri"] == uri:
            for child in cls.get("children", []):
                result.add(child["uri"])
                result |= _all_descendants(child["uri"], cls["children"])
        else:
            result |= _all_descendants(uri, cls.get("children", []))
    return result


def _flatten_uris(classes: list) -> set:
    """Return all URIs in the tree (including nested)."""
    result = set()
    for cls in classes:
        result.add(cls["uri"])
        result |= _flatten_uris(cls.get("children", []))
    return result


@callback(
    Output("store-sources", "data", allow_duplicate=True),
    Input({"type": "scope-checkbox", "index": ALL}, "value"),
    State("store-sources",  "data"),
    State("store-ontology", "data"),
    prevent_initial_call=True,
)
def update_scope(checkbox_values, sources, ontology_store):
    if not sources:
        return no_update

    ontology = ontology_store or {}

    # Find which checkbox changed
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update

    raw       = triggered["index"]   # "{source_id}::{class_uri}"
    source_id, toggled_uri = raw.split("::", 1)

    # Find the triggering checkbox value
    toggled_value = next(
        (item["value"] for item in ctx.inputs_list[0]
         if item["id"]["index"] == raw),
        False,
    )

    # Get ontology tree for this source (for cascade)
    tree_classes = ontology.get(source_id, {}).get("classes", [])
    descendants  = _all_descendants(toggled_uri, tree_classes)

    updated = []
    for s in sources:
        if s["id"] != source_id:
            updated.append(s)
            continue

        s = dict(s)
        current_scope = set(s.get("scope") or [])

        if toggled_value:
            # Check: add this URI + all descendants
            current_scope.add(toggled_uri)
            current_scope |= descendants
        else:
            # Uncheck: remove this URI + all descendants
            current_scope.discard(toggled_uri)
            current_scope -= descendants

        # None = full graph (no filter applied)
        s["scope"] = sorted(current_scope) if current_scope else None
        updated.append(s)

    return updated