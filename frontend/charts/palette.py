ACCENT = "#5B6EF5"
GREY   = "#E9EDF5"
COLORS = [ACCENT, "#F5A05B", "#5BF5A0", "#F55B6E"]


def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    """Convert a 6-digit hex colour to an rgba() string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def base_layout(**kwargs) -> dict:
    """
    Returns a dict of Plotly layout properties shared by every chart.
    Pass extra kwargs to override or extend (e.g. height, margin).
    """
    return dict(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="inherit", size=12),
        **kwargs,
    )