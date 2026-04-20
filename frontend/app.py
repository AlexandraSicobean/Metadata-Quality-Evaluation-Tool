import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from layout.sidebar import build_sidebar, build_add_source_modal

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

server = app.server

app.layout = dbc.Container(
    fluid=True,
    children=[

        # ── Stores ────────────────────────────────────────────────────────
        dcc.Store(id="store-sources", data=[]),
        dcc.Store(id="store-results", data=None),
        dcc.Store(id="store-ui", data={
            "active_metric": None,
            "active_class":  None,
            "prop_view":     "missing",
        }),

        # Maps metric_id → dimension string, populated by populate_metrics.
        # Used by metric card grouping without re-fetching from the backend.
        dcc.Store(id="store-metric-dims", data={}),

        # ── Modal ─────────────────────────────────────────────────────────
        build_add_source_modal(),

        # ── Top bar ───────────────────────────────────────────────────────
        dbc.Row(
            dbc.Col(
                html.H4(
                    "Metadata Quality Evaluator",
                    className="my-3 text-muted fw-light",
                )
            )
        ),

        # ── Main area ─────────────────────────────────────────────────────
        dbc.Row([
            dbc.Col(build_sidebar(), width=3),
            dbc.Col(id="main-panel", width=9, children=[]),
        ]),
    ]
)

# Register all callbacks by importing the modules.
# The decorators fire on import; order does not matter.
import callbacks.sources      # noqa: F401, E402
import callbacks.evaluation   # noqa: F401, E402
import callbacks.main_panel   # noqa: F401, E402
import callbacks.ui            # noqa: F401, E402


if __name__ == "__main__":
    app.run(debug=True, port=8050)