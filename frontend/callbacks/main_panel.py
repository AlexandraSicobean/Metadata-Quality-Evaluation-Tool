from dash import Input, Output, callback

from layout.main_panel import build_guide, build_error, build_analysis, build_comparison


@callback(
    Output("main-panel",  "children"),
    Output("store-ui",    "data", allow_duplicate=True),
    Input("store-results", "data"),
    prevent_initial_call=True,
)
def render_main_panel(results):
    reset_ui = {"active_metric": None, "active_class": None}

    if results is None:
        return build_guide(), reset_ui
    if results.get("status") == "error":
        return build_error(results.get("error_message", "Unknown error.")), reset_ui

    datasets = results.get("datasets", [])

    if results.get("mode") == "analysis":
        return build_analysis(datasets, active_metric_id=None), reset_ui
    if results.get("mode") == "comparison":
        return build_comparison(datasets, active_metric_id=None), reset_ui

    return build_guide(), reset_ui