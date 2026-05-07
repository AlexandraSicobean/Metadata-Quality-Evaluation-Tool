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
    Range-box chart: one box per dataset per class.

    Each box spans min → max as a thin semi-transparent filled rectangle,
    with a solid vertical line at the mean inside it.
    When min == max == mean (all records identical) a dot is shown instead.

    Multiple datasets sharing a class are stacked vertically within the
    row using fractional y offsets. The y-axis is numeric with class names
    as tick labels so sub-row positioning works cleanly.

    Returns None if no class_statistics are present.
    """
    all_classes: list[str] = []
    for d in ds_details:
        for uri in d["details"].get("class_statistics", {}):
            if uri not in all_classes:
                all_classes.append(uri)

    if not all_classes:
        return None

    n_ds         = len(ds_details)
    n_classes    = len(all_classes)
    class_labels = [_short_uri(c) for c in all_classes]
    uri_to_row   = {uri: i for i, uri in enumerate(all_classes)}

    # Half-height of each box in y-axis units — narrower with more datasets
    box_half = 0.28 / n_ds

    # Vertical centre of each dataset within its row
    if n_ds == 1:
        centres = [0.0]
    else:
        span    = 0.55
        step    = span / (n_ds - 1)
        centres = [-span / 2 + i * step for i in range(n_ds)]

    def _hex_rgba(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig = go.Figure()

    for ds_idx, d in enumerate(ds_details):
        stats  = d["details"].get("class_statistics", {})
        color  = d["color"]
        label  = d["label"]
        centre = centres[ds_idx]

        box_x, box_y   = [], []
        mean_x, mean_y = [], []
        dot_x, dot_y   = [], []
        hover_x, hover_y, hover_custom = [], [], []

        for uri in all_classes:
            if uri not in stats:
                continue
            s             = stats[uri]
            mn, mean, mx  = s["min"], s["mean"], s["max"]
            row           = uri_to_row[uri]
            yc            = row + centre
            ylo, yhi      = yc - box_half, yc + box_half

            if abs(mx - mn) < 1e-9:
                # Point value — dot only, no box
                dot_x.append(mean)
                dot_y.append(yc)
            else:
                # Filled rectangle path (clockwise, closed)
                box_x += [mn, mx, mx, mn, mn, None]
                box_y += [ylo, ylo, yhi, yhi, ylo, None]

            # Vertical mean line inside the box
            mean_x += [mean, mean, None]
            mean_y += [ylo, yhi, None]

            # Invisible wide marker for hover
            hover_x.append(mean)
            hover_y.append(yc)
            hover_custom.append((_short_uri(uri), mn, mean, mx))

        fill_color = _hex_rgba(color, 0.20)

        # Filled box
        if box_x:
            fig.add_scatter(
                x=box_x, y=box_y,
                mode="lines", fill="toself",
                fillcolor=fill_color,
                line=dict(color=color, width=1.5),
                showlegend=False, hoverinfo="none",
            )

        # Mean line
        if mean_x:
            fig.add_scatter(
                x=mean_x, y=mean_y,
                mode="lines",
                line=dict(color=color, width=2.5),
                showlegend=False, hoverinfo="none",
            )

        # Point-value dot
        if dot_x:
            fig.add_scatter(
                x=dot_x, y=dot_y,
                mode="markers",
                marker=dict(color=color, size=8, symbol="circle",
                            line=dict(color="white", width=1.5)),
                showlegend=False, hoverinfo="none",
            )

        # Legend entry + hover (invisible wide markers)
        if hover_x:
            fig.add_scatter(
                x=hover_x, y=hover_y,
                mode="markers",
                marker=dict(color=color, size=16, opacity=0),
                name=label,
                customdata=hover_custom,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"{label}<br>"
                    "Mean: %{customdata[2]:.1%}<br>"
                    "Min: %{customdata[1]:.1%} · Max: %{customdata[3]:.1%}"
                    "<extra></extra>"
                ),
            )

    row_height = 60 + (n_ds - 1) * 24
    fig.update_layout(base_layout(
        height=max(180, n_classes * row_height + 80),
        margin=dict(l=8, r=48, t=8, b=8),
        xaxis=dict(range=[0, 1.05], tickformat=".0%",
                   gridcolor="rgba(0,0,0,0.05)",
                   title="Completeness"),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(n_classes)),
            ticktext=class_labels,
            automargin=True,
            range=[-0.5, n_classes - 0.5],
            gridcolor="rgba(0,0,0,0.04)",
        ),
        showlegend=n_ds > 1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
    ))
    return fig




def class_completeness_violin(
    ds_details: list[dict],
) -> go.Figure | None:
    """
    Violin plot of per-record completeness scores grouped by class.

    Layout strategy:
    - Each class occupies one row on the y-axis (integer position).
    - When multiple datasets share a class, each dataset gets its own
      sub-row by offsetting the y-position by a small amount, and each
      violin is given a fixed bandwidth so the shapes are readable.
    - Single unique value → dot instead of violin.
    - Mean line shown inside each violin.
    """
    all_classes: list[str] = []
    for d in ds_details:
        for uri in d["details"].get("class_statistics", {}):
            if uri not in all_classes:
                all_classes.append(uri)

    if not all_classes:
        return None

    has_scores = any(
        d["details"].get("class_statistics", {}).get(uri, {}).get("scores")
        for d in ds_details for uri in all_classes
    )
    if not has_scores:
        return None

    n_ds         = len(ds_details)
    n_classes    = len(all_classes)
    class_labels = [_short_uri(c) for c in all_classes]
    uri_to_row   = {uri: i for i, uri in enumerate(all_classes)}
    PALETTE      = ["#5B6EF5", "#F5A05B", "#5BF5A0", "#F55B6E"]

    # Vertical offsets so datasets don't overlap within a row.
    # Each violin is drawn at row + offset, then the y-axis tick is placed
    # at the integer row centre.
    if n_ds == 1:
        offsets = [0.0]
    else:
        span    = 0.6 * (n_ds - 1) / n_ds
        offsets = [-span/2 + i * span/(n_ds-1) for i in range(n_ds)]

    # Violin half-bandwidth in y-axis units — shrinks with more datasets
    bandwidth = 0.28 / n_ds

    fig = go.Figure()

    for ds_idx, d in enumerate(ds_details):
        stats  = d["details"].get("class_statistics", {})
        color  = PALETTE[ds_idx % len(PALETTE)]
        label  = d["label"]
        offset = offsets[ds_idx]

        for cls_idx, uri in enumerate(all_classes):
            cls_data = stats.get(uri)
            if not cls_data:
                continue
            scores = cls_data.get("scores", [])
            if not scores:
                continue

            row = uri_to_row[uri]
            yc  = row + offset

            unique = set(round(s, 3) for s in scores)

            if len(unique) == 1:
                # Point value — dot
                fig.add_scatter(
                    x=[scores[0]],
                    y=[yc],
                    mode="markers",
                    name=label,
                    legendgroup=label,
                    showlegend=(cls_idx == 0),
                    marker=dict(color=color, size=9, symbol="circle",
                                line=dict(color="white", width=1.5)),
                    hovertemplate=(
                        f"<b>{_short_uri(uri)}</b><br>"
                        f"Dataset: {label}<br>"
                        f"Records in class: {len(scores):,}<br>"
                        f"All records score: {round(scores[0]*100)}%"
                        "<extra></extra>"
                    ),
                )
            else:
                # Build a KDE violin manually using y as the numeric position.
                # We pass y as a constant array (all = yc) so Plotly centres
                # the violin on that position.
                import statistics as _st
                n      = len(scores)
                mean   = round(_st.mean(scores) * 100, 1)
                median = round(_st.median(scores) * 100, 1)
                mn     = round(min(scores) * 100, 1)
                mx     = round(max(scores) * 100, 1)

                # Violin hovertemplate cannot suppress the default stats box,
                # so we use a transparent scatter on top as the hover target
                # and disable hover on the violin itself.
                fig.add_violin(
                    x=scores,
                    y=[yc] * len(scores),
                    name=label,
                    legendgroup=label,
                    showlegend=(cls_idx == 0),
                    orientation="h",
                    line_color=color,
                    fillcolor=color,
                    opacity=0.65,
                    width=bandwidth * 2,
                    meanline=dict(visible=True, color="white", width=2),
                    points=False,
                    scalemode="width",
                    hoverinfo="none",   # suppress default kde/q1/q3 tooltip
                )

                # Invisible wide scatter sitting on top — provides clean hover
                fig.add_scatter(
                    x=[mean / 100],   # hover target at the mean
                    y=[yc],
                    mode="markers",
                    marker=dict(size=18, opacity=0, color=color),
                    name=label,
                    legendgroup=label,
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{_short_uri(uri)}</b><br>"
                        f"Dataset: {label}<br>"
                        f"Records in class: {n:,}<br>"
                        f"Mean completeness: {mean}%<br>"
                        f"Median completeness: {median}%<br>"
                        f"Best record: {mx}%<br>"
                        f"Worst record: {mn}%"
                        "<extra></extra>"
                    ),
                )

    row_height = 70 + (n_ds - 1) * 30

    fig.update_layout(base_layout(
        height=max(220, n_classes * row_height + 100),
        margin=dict(l=8, r=48, t=8, b=8),
        violinmode="overlay",
        violingap=0,
        violingroupgap=0,
        xaxis=dict(
            range=[-0.05, 1.05],
            tickformat=".0%",
            gridcolor="rgba(0,0,0,0.05)",
            title="Completeness score",
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(n_classes)),
            ticktext=class_labels,
            automargin=True,
            range=[-0.55, n_classes - 0.45],
            gridcolor="rgba(0,0,0,0.04)",
            zeroline=False,
        ),
        showlegend=n_ds > 1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
    ))
    return fig