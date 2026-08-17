"""
Charts for the connectivity metric.

Two views: a reachable/unreachable donut per dataset, and a horizontal
bar chart of unreachable URIs grouped by failure classification.
"""

import plotly.graph_objects as go
from charts.palette import COLORS, base_layout

# Human-readable labels for the backend's classification buckets.
# "ok" is deliberately excluded — it means "reachable", not a failure
# reason, and is represented by the donut instead of the reason chart.
#
# not_found/access_denied/rate_limited are kept as separate bars rather
# than folded into one "client error" bucket, since they carry very
# different weight: a 404/410 plausibly means the resource is gone,
# while a 401/403/429 is often just a server blocking automated
# clients — see connectivity.py's module docstring for the reasoning.
_CLASSIFICATION_LABELS = {
    "not_found":        "Not found (404/410)",
    "access_denied":    "Access denied (401/403)",
    "rate_limited":     "Rate limited (429)",
    "client_error":     "Other client error (4xx)",
    "server_error":     "Server error (5xx)",
    "timeout":          "Timeout",
    "connection_error": "Connection error",
    "dns_error":        "DNS error",
    "redirect_loop":    "Redirect loop",
    "invalid_uri":      "Invalid URI",
}


def reachability_donut(ds_details: list[dict]) -> go.Figure:
    """
    Donut chart showing reachable vs unreachable URIs.

    One donut per dataset, arranged in a row using subplots — mirrors
    the language_tag_donut pattern in foundational_format_consistency.
    Both "Reachable" and "Unreachable" always appear in the legend via
    dummy scatter traces, even when one slice has zero count.

    Parameters
    ----------
    ds_details : list[dict]
        Per-dataset detail dicts from collect_ds_details.

    Returns
    -------
    go.Figure
    """
    from plotly.subplots import make_subplots

    n          = len(ds_details)
    top_margin = 56 if n > 1 else 16
    fig = make_subplots(
        rows=1, cols=n,
        specs=[[{"type": "pie"}] * n],
        subplot_titles=[d["label"] for d in ds_details] if n > 1 else [],
    )

    all_labels = ["Reachable", "Unreachable"]
    all_colors = {"Reachable": "#2ECC71", "Unreachable": "#F55B6E"}

    for i, d in enumerate(ds_details):
        det           = d["details"]
        total         = det.get("total_checked", 0)
        unreachable   = det.get("unreachable_count", 0)
        reachable     = max(0, total - unreachable)

        if total == 0:
            values, labels, colors = [1], ["No data"], ["#dee2e6"]
        else:
            values, labels, colors = [], [], []
            if reachable > 0:
                values.append(reachable)
                labels.append("Reachable")
                colors.append(all_colors["Reachable"])
            if unreachable > 0:
                values.append(unreachable)
                labels.append("Unreachable")
                colors.append(all_colors["Unreachable"])

        fig.add_pie(
            row=1, col=i + 1,
            values=values,
            labels=labels,
            marker_colors=colors,
            hole=0.55,
            textinfo="percent",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Count: %{value:,}<br>"
                "Share: %{percent}<extra></extra>"
            ),
            showlegend=False,
        )

    for label in all_labels:
        fig.add_scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(color=all_colors[label], size=10, symbol="square"),
            name=label,
            showlegend=True,
        )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    fig.update_layout(base_layout(
        height=260,
        margin=dict(l=8, r=100, t=top_margin, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15,
                    xanchor="center", x=0.5),
    ))
    return fig


def failure_reason_chart(ds_details: list[dict]) -> go.Figure | None:
    """
    Horizontal bar chart of unreachable URI counts by failure
    classification (timeout, DNS error, 4xx, etc.).

    Parameters
    ----------
    ds_details : list[dict]
        Per-dataset detail dicts from collect_ds_details.

    Returns
    -------
    go.Figure | None
        None if every checked URI was reachable.
    """
    all_reasons: list[str] = []
    reason_data: list[dict] = []

    for d in ds_details:
        by_reason = {
            _CLASSIFICATION_LABELS.get(e["classification"], e["classification"]): e["count"]
            for e in d["details"].get("by_classification", [])
            if e["classification"] != "ok"
        }
        reason_data.append(by_reason)
        for r in by_reason:
            if r not in all_reasons:
                all_reasons.append(r)

    if not all_reasons:
        return None

    all_reasons.sort(
        key=lambda r: sum(rd.get(r, 0) for rd in reason_data),
        reverse=True,
    )

    comparison = len(ds_details) > 1
    fig = go.Figure()
    for i, (d, by_reason) in enumerate(zip(ds_details, reason_data)):
        vals = [by_reason.get(r, 0) for r in all_reasons]
        fig.add_bar(
            name=d["label"],
            y=all_reasons,
            x=vals,
            orientation="h",
            marker_color=COLORS[i % len(COLORS)] if comparison else "#5B6EF5",
            text=[str(v) if v > 0 else "" for v in vals],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Count: %{x:,}<extra></extra>",
            showlegend=comparison,
        )

    fig.update_layout(base_layout(
        height=max(160, len(all_reasons) * 40 + 80),
        margin=dict(l=160, r=48, t=8, b=8),
        barmode="group",
        xaxis=dict(title="Unreachable URI count",
                   gridcolor="rgba(0,0,0,0.05)"),
        yaxis=dict(
            automargin=True,
            tickmode="array",
            tickvals=all_reasons,
            ticktext=all_reasons,
        ),
        showlegend=comparison,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
    ))
    return fig
