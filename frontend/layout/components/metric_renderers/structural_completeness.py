from dash import html, dcc
import dash_bootstrap_components as dbc

import charts.structural_completeness as charts
from layout.components.common import panel_card, section_label, score_badge
from layout.components.detail_views_helpers import (
    collect_ds_details,
    analysis_header,
    comparison_header,
)

METRIC_ID = "structural_completeness"


def render(metric: dict, datasets: list[dict]) -> html.Div:
    """
    Three panels:
      1. Record completeness distribution histogram
      2. Class-level completeness (mean ± range)
      3. Summary statistics table
    """
    ds_details = collect_ds_details(datasets, METRIC_ID)
    comparison = len(ds_details) > 1

    if not ds_details:
        return html.Div()

    header = (
        comparison_header("Structural Completeness", ds_details)
        if comparison else
        analysis_header("Structural Completeness", ds_details[0]["score"])
    )

    dist_section = panel_card([
        section_label("Record completeness distribution"),
        dcc.Graph(
            figure=charts.score_distribution(ds_details),
            config={"displayModeBar": False},
        ),
    ])

    class_fig = charts.class_completeness(ds_details)
    class_section = panel_card([
        section_label("Class-level completeness (mean ± range)"),
        dcc.Graph(figure=class_fig, config={"displayModeBar": False}),
    ]) if class_fig else html.Div()

    stats_section = _summary_table(ds_details, comparison)

    return html.Div([header, dist_section, class_section, stats_section])


# ── Private helpers ───────────────────────────────────────────────────────

def _summary_table(ds_details: list[dict], comparison: bool) -> dbc.Card:
    col_headers = (
        [html.Th("")] + [html.Th(d["label"]) for d in ds_details]
        if comparison else [html.Th(""), html.Th("Value")]
    )
    stat_rows = []
    for key, fmt in [
        ("total_records",              lambda v: str(v)),
        ("median_record_completeness", lambda v: f"{round(v*100)}%"),
        ("min_record_completeness",    lambda v: f"{round(v*100)}%"),
        ("max_record_completeness",    lambda v: f"{round(v*100)}%"),
        ("profile",                    str),
    ]:
        vals = [
            fmt(d["details"][key]) if d["details"].get(key) is not None else "—"
            for d in ds_details
        ]
        stat_rows.append(html.Tr(
            [html.Td(html.Strong(key.replace("_", " ").title(),
                                 style={"fontSize": "0.82rem"}))]
            + [html.Td(v, style={"fontSize": "0.82rem"}) for v in vals]
        ))

    # Prefix each warning with the dataset label so the user knows
    # which source triggered it (important when multiple sources fail).
    warnings = [
        (d["label"], d["details"]["warning"])
        for d in ds_details
        if d["details"].get("warning")
    ]

    return panel_card([
        section_label("Summary statistics"),
        dbc.Table(
            [html.Thead(html.Tr(col_headers)), html.Tbody(stat_rows)],
            bordered=True, size="sm", className="mb-2",
        ),
        html.Div([
            dbc.Alert(
                [html.Strong(f"{lbl}: "), w],
                color="warning", className="py-2 mb-2",
                style={"fontSize": "0.82rem"},
            )
            for lbl, w in warnings
        ]) if warnings else html.Div(),
    ])