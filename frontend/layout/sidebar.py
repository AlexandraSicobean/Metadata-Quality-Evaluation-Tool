from dash import html, dcc
import dash_bootstrap_components as dbc


def build_sidebar() -> html.Div:
    return html.Div([
        _sources_section(),
        html.Hr(className="my-3"),
        _metrics_section(),
        html.Hr(className="my-3"),
        _run_section(),
    ])


# ── Section builders ───────────────────────────────────────────────────────

def _sources_section() -> html.Div:
    return html.Div([
        html.P(
            "Data Sources",
            className="text-muted text-uppercase fw-semibold mb-2",
            style={"fontSize": "0.75rem", "letterSpacing": "0.08em"}
        ),
        html.Div(id="source-list"),
        dbc.Button(
            "+ Add Source",
            id="btn-add-source",
            color="primary",
            outline=True,
            size="sm",
            className="mt-2 w-100",
        ),
    ])


def _metrics_section() -> html.Div:
    return html.Div([
        html.P(
            "Quality Metrics",
            className="text-muted text-uppercase fw-semibold mb-2",
            style={"fontSize": "0.75rem", "letterSpacing": "0.08em"}
        ),
        # Populated on startup by callbacks/sources.py → populate_metrics.
        # Each accordion item is one quality category (Intrinsic, Contextual…)
        # containing a checklist of its metrics.
        html.Div(id="metric-accordion"),
        # Hidden master store of all selected metric ids — read by the run
        # button callback and the evaluation callback.
        dcc.Store(id="metric-selection", data=[]),
    ])


def _run_section() -> html.Div:
    from dash import dcc
    return html.Div([
        # dcc.Loading shows a spinner over the button while the evaluation
        # callback is running, giving the user clear "in progress" feedback.
        dcc.Loading(
            id="loading-run",
            type="circle",
            color="#5B6EF5",
            children=dbc.Button(
                "Run Evaluation",
                id="btn-run-evaluation",
                color="primary",
                size="sm",
                className="w-100 mb-2",
                disabled=True,
            ),
        ),
        html.Div(
            id="run-feedback",
            className="text-muted",
            style={"fontSize": "0.8rem"},
        ),
    ])


# ── Source list item ───────────────────────────────────────────────────────

def build_source_item(source: dict) -> dbc.Card:
    """
    One card per source in the sidebar list.
    Shows label + type badge, a pencil (edit) button, and a ✕ (delete) button.
    """
    source_id   = source["id"]
    label       = source["label"]
    selected    = source["selected"]
    config_type = source["source_config"]["type"]

    type_badge = dbc.Badge(
        "File" if config_type == "rdf_file" else "SPARQL",
        color="secondary",
        className="ms-1",
        style={"fontSize": "0.65rem"},
    )

    return dbc.Card(
        dbc.CardBody(
            dbc.Row([

                # Checkbox + label
                dbc.Col(
                    dbc.Checkbox(
                        id={"type": "source-checkbox", "index": source_id},
                        value=selected,
                        label=html.Span([label, type_badge]),
                    ),
                    width=8,
                    className="d-flex align-items-center",
                ),

                # Edit button
                dbc.Col(
                    dbc.Button(
                        "✎",
                        id={"type": "btn-edit-source", "index": source_id},
                        color="link",
                        size="sm",
                        className="text-muted p-0",
                        style={"lineHeight": "1", "fontSize": "0.9rem"},
                        title="Edit source",
                    ),
                    width=2,
                    className="d-flex align-items-center justify-content-end",
                ),

                # Delete button
                dbc.Col(
                    dbc.Button(
                        "✕",
                        id={"type": "btn-delete-source", "index": source_id},
                        color="link",
                        size="sm",
                        className="text-muted p-0",
                        style={"lineHeight": "1"},
                        title="Delete source",
                    ),
                    width=2,
                    className="d-flex align-items-center justify-content-end",
                ),

            ], align="center", className="g-0"),
            className="py-2 px-2",
        ),
        className="mb-1",
        style={"border": "1px solid #dee2e6"},
    )


# ── Add / Edit Source modal ────────────────────────────────────────────────

def build_add_source_modal() -> dbc.Modal:
    """
    Modal used for both adding and editing a source.

    - "modal-title"     — text swapped by callback ("Add" vs "Edit")
    - "modal-edit-id"   — hidden store carrying the id of the source being
                          edited, or None when adding a new one
    """
    return dbc.Modal([
        dbc.ModalHeader(
            dbc.ModalTitle("Add Data Source", id="modal-title")
        ),
        dbc.ModalBody([

            # Hidden store: source id when editing, None when adding
            dcc.Store(id="modal-edit-id", data=None),

            dbc.Label("Label", html_for="input-source-label"),
            dbc.Input(
                id="input-source-label",
                placeholder="e.g. My Local Dataset",
                className="mb-3",
            ),

            dbc.Label("Source type"),
            dbc.RadioItems(
                id="input-source-type",
                options=[
                    {"label": "RDF File",        "value": "rdf_file"},
                    {"label": "SPARQL Endpoint", "value": "sparql_endpoint"},
                ],
                value="rdf_file",
                className="mb-3",
            ),

            # RDF File fields
            html.Div(
                id="source-fields-rdf",
                children=[
                    dbc.Label("File path", html_for="input-file-path"),
                    dbc.Input(
                        id="input-file-path",
                        placeholder="e.g. data/my_dataset.ttl",
                        className="mb-2",
                    ),
                    dbc.Label("Format", html_for="input-file-format"),
                    dbc.Select(
                        id="input-file-format",
                        options=[
                            {"label": "Turtle (.ttl)",   "value": "turtle"},
                            {"label": "RDF/XML (.rdf)",  "value": "xml"},
                            {"label": "N-Triples (.nt)", "value": "nt"},
                            {"label": "N3 (.n3)",        "value": "n3"},
                        ],
                        value="turtle",
                    ),
                ],
            ),

            # SPARQL Endpoint fields
            html.Div(
                id="source-fields-sparql",
                style={"display": "none"},
                children=[
                    dbc.Label("Endpoint URL", html_for="input-endpoint-url"),
                    dbc.Input(
                        id="input-endpoint-url",
                        placeholder="e.g. https://dbpedia.org/sparql",
                        className="mb-2",
                    ),
                    dbc.Label("CONSTRUCT query", html_for="input-sparql-query"),
                    dbc.Textarea(
                        id="input-sparql-query",
                        placeholder="CONSTRUCT { ?s ?p ?o } WHERE { ... }",
                        rows=5,
                    ),
                ],
            ),

            html.Div(
                id="modal-source-feedback",
                className="mt-2 text-danger",
                style={"fontSize": "0.8rem"},
            ),
        ]),

        dbc.ModalFooter([
            dbc.Button(
                "Cancel",
                id="btn-modal-cancel",
                color="secondary",
                outline=True,
                className="me-2",
            ),
            dbc.Button(
                "Save",
                id="btn-modal-confirm",
                color="primary",
            ),
        ]),
    ],
        id="modal-add-source",
        is_open=False,
        backdrop="static",
    )