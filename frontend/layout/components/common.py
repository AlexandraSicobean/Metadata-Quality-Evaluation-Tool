from dash import html
import dash_bootstrap_components as dbc

from charts.palette import ACCENT


def card(children, className: str = "h-100", **kwargs) -> dbc.Card:
    """Standard card wrapper used in stat rows and chart panels."""
    return dbc.Card(
        dbc.CardBody(children, className="p-3"),
        className=className,
        **kwargs,
    )


def stat_card(label: str, value) -> dbc.Col:
    """
    A single stat display column (Triples / Entities / Classes).
    Renders '—' when value is None.
    """
    return dbc.Col(
        card([
            html.P(
                label,
                className="text-muted mb-1",
                style={"fontSize": "0.75rem", "textTransform": "uppercase",
                       "letterSpacing": "0.06em"},
            ),
            html.H4(
                str(value) if value is not None else "—",
                className="mb-0 fw-semibold",
            ),
        ]),
        xs=6, md=3,
        className="mb-3",
    )


def panel_card(children) -> dbc.Card:
    """Card used inside the detail panel sections."""
    return dbc.Card(
        dbc.CardBody(children, className="p-3"),
        className="mb-3",
    )


def section_label(text: str) -> html.P:
    """Small uppercase muted section heading."""
    return html.P(
        text,
        className="text-muted fw-semibold mb-2",
        style={"fontSize": "0.75rem", "textTransform": "uppercase",
               "letterSpacing": "0.06em"},
    )


def score_badge(score: float) -> dbc.Badge:
    """Coloured % badge — green ≥75%, amber ≥40%, red <40%."""
    pct   = round(score * 100)
    color = "success" if pct >= 75 else "warning" if pct >= 40 else "danger"
    return dbc.Badge(f"{pct}%", color=color, className="ms-2 fs-6")