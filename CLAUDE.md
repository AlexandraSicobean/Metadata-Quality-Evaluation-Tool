# ECHOES Metadata Quality Evaluation Tool

A visualization-driven metadata quality evaluation tool for digital cultural heritage Linked Data, built as part of the ECHOES European cultural heritage initiative. This is also the subject of a master's thesis: "A Visualization Tool for Metadata Quality Evaluation in Digital Cultural Heritage."

Two independently runnable applications communicate over HTTP:

- **backend/** — FastAPI, does all evaluation logic
- **frontend/** — Plotly Dash, interactive dashboard
- A **CLI** (`backend/cli/cli.py`) provides a server-free entry point into the same evaluation pipeline for scripted/reproducible workflows.

## Technology Stack

**Backend:** Python, FastAPI (API layer, Pydantic request/response validation), Uvicorn (ASGI server), RDFLib (RDF parsing/serialization/SPARQL), pySHACL (SHACL validation), SPARQLWrapper (remote SPARQL endpoints), PyYAML (CLI config files).

**Frontend:** Plotly Dash, Dash Bootstrap Components (DBC).

## Project Structure

```
backend/
    api/                     FastAPI endpoints and request handling
        evaluation_controller     the API layer implementation
    cli/                     Command-line interface (cli.py)
    config/                  Metric configuration (metrics_config.json)
    datasource/              Data source abstraction (Strategy + Factory)
    engine/                  Evaluation Engine orchestration (evaluation_engine.py)
    graph/                   Ontology extraction, graph caching, scope filtering
        graph_cache.py            thread-safe singleton graph cache
        ontology_extractor.py     class/property hierarchy extraction
    export/                  Metric-specific export infrastructure (CSV)
    metrics/                 Plugin interface + metric implementations
        metric_plugin.py          shared plugin interface
        metric_registry.py        identifier -> plugin class registry
        plugins/                  one file per metric (see below)
    models/                  Request, response, and internal (Pydantic) models
    results_aggregator/      Weighted score aggregation (aggregator.py)
frontend/
    app.py                   Dash entry point + top-level layout (2-column grid)
    api_client.py            HTTP client wrapping backend endpoints
    store.py                 Shared application state (dcc.Store) definitions
    callbacks/                All reactive callback modules
        ui.py                     visualization callbacks (store-ui driven)
    layout/                  Layout builder functions
        sidebar.py                data source + metric selection UI
        main_panel.py             build_guide() / build_analysis() / build_comparison()
        components/
            metric_renderers/         one renderer per metric (drilldown UI)
    charts/                  Pure Plotly chart functions, one file per metric,
                             no Dash/UI knowledge
```

Each module maps to a component described in the thesis's System Design chapter. **Dependency direction in the frontend is strict and one-way:** `charts/` -> `layout/components/` -> `layout/{main_panel,sidebar}.py` -> `callbacks/`. No file in a lower layer imports from a higher one. Never introduce a reverse import when adding or refactoring code.

## Backend Architecture

- **API layer** (`api/evaluation_controller`): HTTP interface only — no evaluation logic. Validates/deserializes requests, delegates to the Evaluation Engine or Ontology Extractor, serializes responses. Four endpoints:
    - `GET /metrics` — implemented metrics + metadata, sourced from `config/metrics_config.json`. Metric names are **never hardcoded in the frontend**; adding a metric to config alone surfaces it in the UI.
    - `GET /dimensions` — the four quality dimensions (Intrinsic, Contextual, Representational, Accessibility), same config file.
    - `POST /ontology` — lazy class-hierarchy extraction for scope filtering; reads from graph cache if already loaded.
    - `POST /evaluate` — runs selected metrics for the given datasets. 400 if a metric identifier is unrecognized; 500 if a registered identifier has no plugin implementation (configuration inconsistency, not user error).
    - `GET /export/{dataset_id}/{metric_id}/{category}` — streams CSV of cached export rows; 404 if no matching export data exists.
- **CLI** (`cli/cli.py`): same pipeline as the API. Commands: `--config` (run a YAML evaluation config), `--inspect` (ontology/class hierarchy), `--template` (print an annotated example config), `--list-metrics`, `--help`. Config format intentionally mirrors the API's internal request models. Relative output paths resolve against the CLI directory, not the current working directory.
- **Evaluation Engine** (`engine/evaluation_engine.py`): orchestrator only — never implement data loading or metric computation here. Pipeline per request: Data Source loads graph (via `DataSourceFactory`) -> optional scope filter -> wrap in `DatasetContext` -> run each selected metric plugin -> pass results to `ResultAggregator` -> attach graph statistics. **Scope filtering is engine-level, not metric-level** — do not reintroduce per-metric scope logic.
- **Data Source** (`datasource/`): Strategy + Factory. `RDFFileSource` and `SPARQLEndpointSource` both implement a single `load()` interface and return `rdflib.Graph`. Format inferred from file extension if not explicit. SPARQL side uses CONSTRUCT queries (not SELECT) so results parse directly into a graph; queries must be single-line in JSON bodies (multiline breaks Wikidata/DBpedia with 502/422 errors).
- **Graph cache** (`graph/graph_cache.py`): thread-safe singleton, keyed by SHA-256 hash of the canonical source config (not dataset id/label), protected by `threading.Lock`. Scope-filtered subgraphs are **intentionally not cached** — filtering is cheap in-memory work; the expensive part (parsing/I/O) is already cached at the full-graph level.
- **Ontology Extractor** (`graph/ontology_extractor.py`): builds `ClassNode`/ `PropertyInfo` hierarchy directly from the RDF graph (rdf:type + rdf:subClassOf), no external schema. Independent of the evaluation pipeline — used only for exploration and scope configuration.
- **Metric Plugins** (`metrics/plugins/`): each implements `evaluate(context)` from `metrics/metric_plugin.py`, returns a `MetricResult` (score in [0,1], status `computed`/`failed`/`not_applicable`, metric-specific `details` dict). Registered in `metrics/metric_registry.py` (id -> class) and `config/metrics_config.json` (id -> display metadata + weight). Adding a metric = new plugin class + registry entry + config entry; no other component changes. Use `error_result()` for recoverable failures instead of raising — partial evaluation results must remain available.
    - `structural_completeness.py` — SHACL/EDM profile-based (15 deduplicated properties, score = `1 - violations/15`; structural-issues score = `max(0, 1 - violations/(len(subject_types)+violations))`)
    - `property_coverage.py` — data-driven, per-class fill rates, weighted by class size
    - `multilingual_labeling_coverage.py` — coverage ratio × language-count multiplier (`blank_class_rates` is always `{}` since BNodes have no rdf:type)
    - `foundational_format_consistency.py` — URI validity, datatype correctness, BCP 47 language tags, structural issues (blank nodes, empty literals); each sub-score exported separately via the Export cache
- **Results Aggregator** (`results_aggregator/aggregator.py`): weighted mean of successfully-computed metrics only; returns `None` (not a fabricated score) if nothing is valid. Also computes triple/entity/class counts. Keep aggregation logic isolated from metric implementations.
- **Export infrastructure** (`export/`): thread-safe in-memory cache keyed by `(dataset_id, metric_id, category)`; invalidated whenever the corresponding graph cache entry is invalidated so exports never go stale.

## Frontend Architecture

- **Three stores**, defined centrally in `store.py`:
    - `store-sources` — list of source objects (UUID, label, source type/params, scope class URIs, selected flag). Single source of truth for the source list.
    - `store-results` — full nested evaluation results. `null` -> guide mode; one dataset -> analysis mode; multiple -> comparison mode.
    - `store-ui` — transient UI state (selected metric, active drilldown class). Kept separate from results so navigation doesn't touch evaluation data.
    - (an ontology cache also exists client-side to avoid redundant `/ontology` calls on repeated expand/collapse)
- **Callbacks** (`callbacks/`) fall into three categories: configuration (sources, metric selection, lazy ontology loading), evaluation (validates >=1 source and >=1 metric, calls the API, normalizes into `store-results`), and visualization (`callbacks/ui.py` — drilldown, CSV export, active-card styling). Callbacks never talk to each other directly; only through the stores.
- **Layout**: `app.py` is the 3/9-column Bootstrap grid root. `layout/sidebar.py` builds data-source cards (`build_source_item()`) and the metric accordion. `layout/ main_panel.py` dispatches on `store-results` via `build_guide()` / `build_analysis()` / `build_comparison()`.
- **Charts** (`charts/`): pure functions, plain Python data in, Plotly `Figure` out, no Dash imports. One file per metric plus `overview.py`. Known gotcha: `fig.add_shape` creates a cartesian axis that clears background fills — use `add_scatter(mode="lines")` for background zone overlays instead.

## Design Principles (do not violate without discussion)

1. **Dual interaction model** — API and CLI share one evaluation pipeline; never fork logic between them.
2. **Layered modular monolith**, not microservices — keep module boundaries clean so it _could_ be split later, but don't add deployment-level separation now.
3. **Plugin-based metrics** — new metrics are additive (plugin + registry + config), never require touching the engine.
4. **Data source abstraction** — Strategy + Factory; new source types are new strategy classes, not branches in existing code.
5. **Evaluation Engine orchestrates only** — no business logic in the engine itself.
6. **Scope filtering is engine-level** — applied once, before metrics run; not duplicated per-metric.
7. **Centralized frontend state** — components communicate only through the three stores, never directly.

## Terminology

RDF terminology should be standardized on **"resource"** (not "entity" or "record") — flagged by a thesis reviewer as inconsistent across the tool. This is agreed direction but the sweep across the codebase has not been completed — check with me before doing a mechanical rename in files I haven't confirmed yet.

## Docstrings

Every function/module in this codebase already has a docstring in an established format. This is a hard constraint:

- **Never rewrite or reformat an existing docstring** unless the code it documents changed. Preserve exact structure/sections/wording style.
- **No backticks** around attribute or parameter names in docstrings — this project's convention writes them plain.
- For **new** functions or new code sections, match the style of the nearest existing docstring in the same file (same section headers, same level of detail, same formatting) rather than introducing a different convention.
- If you're ever unsure what the established pattern is for a given file, show me a draft before applying it broadly.

## Working Style

- **Minimal diffs.** Don't refactor unrelated code, rename things, or "clean up" while fixing something else. Ask first if a change seems to need to grow beyond the reported issue.
- **I test in the running app**, not by reading code — when something's visually wrong I'll usually describe it or share a screenshot rather than pointing at a line number. Fixes should be verifiable the same way.
- **I sometimes make local edits directly** (e.g. a color override) and will tell you to preserve them — don't silently revert local changes you didn't make.
- When a fix creates a new problem, just fix it — don't re-explain the failed approach.
- Explain significant design decisions before implementing them; small/obvious fixes don't need a preamble.
- Avoid over-engineering — prefer the simplest solution that respects the separation of concerns above.