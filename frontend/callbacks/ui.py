from dash import Input, Output, State, ALL, callback, ctx, no_update

from layout.components.detail_views import render_detail_panel as _render_detail_panel
from layout.components.metric_renderers.property_completeness import (
    build_analysis_drilldown,
    build_comparison_drilldown,
)


# ── 1. Update active_metric on card click ─────────────────────────────────

@callback(
    Output("store-ui", "data", allow_duplicate=True),
    Input({"type": "metric-card", "index": ALL}, "n_clicks"),
    State("store-ui", "data"),
    prevent_initial_call=True,
)
def update_active_metric(n_clicks_list, ui_state):
    if not any(n for n in (n_clicks_list or []) if n):
        return no_update
    triggered_id = ctx.triggered_id
    if not isinstance(triggered_id, dict):
        return no_update
    clicked = triggered_id["index"]
    current = (ui_state or {}).get("active_metric")
    return {
        **(ui_state or {}),
        "active_metric": None if clicked == current else clicked,
        "active_class":  None,
        "prop_view":     "missing",
    }


# ── 2. Update card border accents ─────────────────────────────────────────
#
# Only re-renders when active_metric changes. Changes to active_class or
# prop_view must NOT trigger this — they would recreate the detail panel
# and wipe the drilldown.

@callback(
    Output({"type": "metric-card", "index": ALL}, "style"),
    Input("store-ui", "data"),
    State({"type": "metric-card", "index": ALL}, "id"),
    State({"type": "metric-card", "index": ALL}, "style"),
    prevent_initial_call=True,
)
def update_card_styles(ui_state, card_ids, current_styles):
    active = (ui_state or {}).get("active_metric")
    new_styles, changed = [], False
    for i, cid in enumerate(card_ids or []):
        is_active = cid["index"] == active
        new_style = {
            "cursor":     "pointer",
            "borderLeft": "3px solid #5B6EF5" if is_active else "1px solid #dee2e6",
            "transition": "border 0.15s",
        }
        new_styles.append(new_style)
        old = (current_styles or [])[i] if i < len(current_styles or []) else {}
        if old.get("borderLeft") != new_style["borderLeft"]:
            changed = True
    return new_styles if changed else [no_update] * len(card_ids or [])


# ── 3. Render the detail panel ────────────────────────────────────────────
#
# Only fires when active_metric changes, NOT on active_class / prop_view.
# Those are handled by render_property_drilldown (callback 6) which writes
# to a nested div, not the full panel.

@callback(
    Output("detail-panel", "children"),
    Input("store-ui",      "data"),
    Input("store-results", "data"),
    State("store-ui",      "data"),   # previous value via triggered check
    prevent_initial_call=True,
)
def render_detail_panel_callback(ui_state, results, _ui_state_prev):
    if not results or results.get("status") == "error":
        return no_update

    # Only re-render the full detail panel when active_metric triggered this.
    # If store-ui changed due to active_class or prop_view, skip — those are
    # handled by the drilldown callback below.
    triggered = ctx.triggered_id
    if triggered == "store-ui":
        # Check if active_metric actually changed vs previous render
        # We can't get the previous value easily, so instead we check:
        # if active_class or prop_view is set, the metric panel is already
        # rendered and we should not wipe it.
        active_class = (ui_state or {}).get("active_class")
        prop_view    = (ui_state or {}).get("prop_view", "missing")
        # Only skip if we're in property_completeness and class is selected
        # or a non-default prop_view — otherwise always re-render
        active_metric = (ui_state or {}).get("active_metric")
        if (active_metric == "property_completeness"
                and (active_class is not None or prop_view != "missing")):
            return no_update

    active_metric_id = (ui_state or {}).get("active_metric")
    return _render_detail_panel(active_metric_id, results)


# ── 4. Update active_class on chart click ─────────────────────────────────

@callback(
    Output("store-ui", "data", allow_duplicate=True),
    Input("property-class-chart", "clickData"),
    State("store-ui", "data"),
    prevent_initial_call=True,
)
def update_active_class(click_data, ui_state):
    if not click_data:
        return no_update
    try:
        raw = click_data["points"][0]["customdata"]
        class_uri = raw[0] if isinstance(raw, (list, tuple)) else raw
    except (KeyError, IndexError, TypeError):
        return no_update
    current = (ui_state or {}).get("active_class")
    return {
        **(ui_state or {}),
        "active_class": None if class_uri == current else class_uri,
        "prop_view":    "missing",
    }


# ── 5. Update prop_view on toggle click ───────────────────────────────────

@callback(
    Output("store-ui", "data", allow_duplicate=True),
    Input("prop-view-missing",   "n_clicks"),
    Input("prop-view-fill_rate", "n_clicks"),
    State("store-ui", "data"),
    prevent_initial_call=True,
)
def update_prop_view(n_missing, n_fill, ui_state):
    triggered = ctx.triggered_id
    if not triggered:
        return no_update
    mode = "missing" if triggered == "prop-view-missing" else "fill_rate"
    return {**(ui_state or {}), "prop_view": mode}


# ── 6. Render property drilldown ──────────────────────────────────────────

@callback(
    Output("property-drilldown-panel", "children"),
    Input("store-ui",      "data"),
    Input("store-results", "data"),
    prevent_initial_call=True,
)
def render_property_drilldown(ui_state, results):
    if (ui_state or {}).get("active_metric") != "property_completeness":
        return no_update
    active_class = (ui_state or {}).get("active_class")
    prop_view    = (ui_state or {}).get("prop_view", "missing")
    comparison   = (results or {}).get("mode") == "comparison"

    if comparison:
        return build_comparison_drilldown(active_class, results or {})
    else:
        return build_analysis_drilldown(active_class, results or {})