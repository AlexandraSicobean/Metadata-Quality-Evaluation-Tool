import plotly.graph_objects as go
from charts.palette import COLORS, base_layout

_BUCKETS = ["0.0","0.1","0.2","0.3","0.4","0.5",
            "0.6","0.7","0.8","0.9","1.0"]


def _bucket_label(b: str) -> str:
    if b == "1.0":
        return "100%"
    v = int(float(b) * 100)
    return f"{v}–{v+9}%"


def _short_uri(uri: str) -> str:
    return uri.split("#")[-1].split("/")[-1]


def score_distribution(
    ds_details: list[dict],
) -> go.Figure:
    """
    Grouped bar chart of per-record completeness score distribution.

    X-axis : completeness buckets (0–9%, 10–19%, … 100%)
    Y-axis : number of records (raw count, not percentage)

    Using raw counts makes the y-axis unambiguous — "200 records" is clearer
    than "24% of records" especially when comparing datasets of different sizes.
    In comparison mode the grouped bars let the user see both absolute counts
    and relative shapes side by side.
    """
    fig = go.Figure()
    labels = [_bucket_label(b) for b in _BUCKETS]

    for d in ds_details:
        raw    = d["details"].get("score_distribution", {})
        counts = [raw.get(b, 0) for b in _BUCKETS]

        fig.add_bar(
            name=d["label"],
            x=labels,
            y=counts,
            marker_color=d["color"],
            text=[str(c) if c > 0 else "" for c in counts],
            textposition="outside",
            hovertemplate="%{x}<br>%{y} records<extra></extra>",
        )

    fig.update_layout(base_layout(
        height=300,
        margin=dict(l=8, r=8, t=8, b=8),
        barmode="group",
        yaxis=dict(
            title="Number of records",
            gridcolor="rgba(0,0,0,0.05)",
        ),
        xaxis=dict(title="Completeness bucket"),
        showlegend=len(ds_details) > 1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
    ))
    return fig


def class_completeness(
    ds_details: list[dict],
) -> go.Figure | None:
    """
    Range line + mean marker per class.

    For each class this renders:
      - a horizontal line spanning min → max  (the full observed range)
      - a filled circle at the mean

    This is honest to the data we actually have (min, mean, max) and avoids
    the bar-from-zero visual which made it look like completeness started at 0.
    In comparison mode each dataset gets its own colour; classes are aligned
    on the y-axis so differences are easy to spot.

    Returns None if no class_statistics are available.
    """
    # Collect all class URIs across datasets (union, preserving first-seen order)
    all_classes: list[str] = []
    for d in ds_details:
        for uri in d["details"].get("class_statistics", {}):
            if uri not in all_classes:
                all_classes.append(uri)

    if not all_classes:
        return None

    class_labels = [_short_uri(c) for c in all_classes]
    fig = go.Figure()

    for d in ds_details:
        stats  = d["details"].get("class_statistics", {})
        color  = d["color"]
        label  = d["label"]

        means, mins, maxs, y_labels = [], [], [], []
        for uri, lbl in zip(all_classes, class_labels):
            if uri in stats:
                means.append(stats[uri]["mean"])
                mins.append(stats[uri]["min"])
                maxs.append(stats[uri]["max"])
                y_labels.append(lbl)

        if not means:
            continue

        # ── Range lines (min → max) ───────────────────────────────────────
        # Plotly has no native horizontal range mark, so we draw one
        # scatter trace per class using None-separated segments.
        x_lines, y_lines = [], []
        for i, (mn, mx, lbl) in enumerate(zip(mins, maxs, y_labels)):
            x_lines += [mn, mx, None]
            y_lines += [lbl, lbl, None]

        fig.add_scatter(
            x=x_lines,
            y=y_lines,
            mode="lines",
            line=dict(color=color, width=3),
            showlegend=False,
            hoverinfo="none",
        )

        # ── Mean markers ──────────────────────────────────────────────────
        fig.add_scatter(
            x=means,
            y=y_labels,
            mode="markers",
            name=label,
            marker=dict(color=color, size=10, symbol="circle",
                        line=dict(color="white", width=2)),
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"{label}<br>"
                "Mean: %{x:.1%}<br>"
                "<extra></extra>"
            ),
            customdata=list(zip(mins, maxs)),
        )

        # ── Min / max tick marks ──────────────────────────────────────────
        for x_val, y_val, mn, mx in zip(means, y_labels, mins, maxs):
            for endpoint in [mn, mx]:
                fig.add_scatter(
                    x=[endpoint, endpoint],
                    y=[y_val],   # single point — just a tick
                    mode="markers",
                    marker=dict(color=color, size=6, symbol="line-ns",
                                line=dict(color=color, width=2)),
                    showlegend=False,
                    hoverinfo="none",
                )

    n = len(all_classes)
    fig.update_layout(base_layout(
        height=max(180, n * 44 + 80),
        margin=dict(l=8, r=48, t=8, b=8),
        xaxis=dict(range=[0, 1.08], tickformat=".0%",
                   gridcolor="rgba(0,0,0,0.05)",
                   title="Completeness"),
        yaxis=dict(automargin=True),
        showlegend=len(ds_details) > 1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
    ))
    return fig