from dash import Input, Output, State, callback, no_update

from api_client import run_evaluation, APIError
from store import make_results


@callback(
    Output("store-results",      "data"),
    Output("btn-run-evaluation", "disabled",  allow_duplicate=True),
    Output("btn-run-evaluation", "children",  allow_duplicate=True),
    Output("run-feedback",       "children",  allow_duplicate=True),
    Input("btn-run-evaluation",  "n_clicks"),
    State("store-sources",    "data"),
    State("metric-selection", "data"),
    prevent_initial_call=True,
)
def run_evaluation_callback(n_clicks, sources, selected_metrics):
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    selected_sources = [s for s in (sources or []) if s.get("selected")]

    if not selected_sources:
        return no_update, no_update, no_update, "Select at least one data source."
    if not selected_metrics:
        return no_update, no_update, no_update, "Select at least one metric."

    # Disable button and show "Running…" for the duration of the call.
    # Because this is a synchronous callback, Dash won't update the UI
    # mid-function — but we return the correct restored label at the end
    # so the button recovers correctly after the call completes.
    label = "Run Analysis" if len(selected_sources) == 1 else "Run Comparison"

    try:
        datasets = run_evaluation(selected_sources, selected_metrics)
    except APIError as exc:
        result = make_results([], error_message=str(exc))
        return result, False, label, ""

    result = make_results(datasets)
    return result, False, label, ""