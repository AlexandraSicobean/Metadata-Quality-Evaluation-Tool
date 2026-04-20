from dash import html
import dash_bootstrap_components as dbc

from charts.palette import COLORS
from layout.components.common import score_badge


def collect_ds_details(
    datasets: list[dict],
    metric_id: str,
) -> list[dict]:
    """
    Extracts metric data from each dataset into a flat list ready for
    chart functions.

    Returns
    -------
    list of dicts:
        {"label": str, "color": str, "details": dict, "score": float}
    One entry per dataset that contains the requested metric_id.
    """
    result = []
    for i, ds in enumerate(datasets):
        m = next(
            (x for x in ds.get("metrics", []) if x["metric_id"] == metric_id),
            None,
        )
        if m:
            result.append({
                "label":   ds.get("label", f"Dataset {i+1}"),
                "color":   COLORS[i % len(COLORS)],
                "details": m.get("details", {}),
                "score":   m["score"],
            })
    return result


def analysis_header(name: str, score: float) -> html.Div:
    """Header row for single-dataset view: metric name + coloured % badge."""
    return dbc.Row([
        dbc.Col(html.H6(name, className="mb-0 fw-semibold"), width="auto"),
        dbc.Col(score_badge(score), width="auto", className="ps-0"),
    ], align="center", className="mb-3")


def comparison_header(name: str, ds_details: list[dict]) -> html.Div:
    """Header row for comparison view: metric name + one badge per dataset."""
    badges = [
        dbc.Badge(
            f"{d['label']}: {round(d['score'] * 100)}%",
            color="secondary",
            className="ms-2",
            style={"backgroundColor": d["color"]},
        )
        for d in ds_details
    ]
    return dbc.Row(
        [dbc.Col(html.H6(name, className="mb-0 fw-semibold"), width="auto")]
        + [dbc.Col(b, width="auto") for b in badges],
        align="center",
        className="mb-3 g-1",
    )