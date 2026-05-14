# Metadata Quality Evaluation Tool
A visualization-based tool for evaluating and comparing multiple dimensions of metadata quality in semantic data, with a focus on Digital Cultural Heritage collections. The tool supports query-based selection of collections, quality dimensions, and visualizes results to enable analysis and comparison within and across collections.

## Architecture
The application is divided into two independent services:
1. Dash Frontend
2. FastAPI Backend
### Frontend
Implemented using:
- Dash
- Plotly
- Dash Bootstrap Components

Responsibilities:
- Dataset configuration
- Metric selection
- Ontology scope filtering
- Interactive visualization
- Analysis and comparison views

### Backend
Implemented using:
- FastAPI
- RDFLib
- pySHACL

Responsibilities:
- Datasorce processing through
	- RDF parsing
	- SPARQL querying
- Metric execution
- Ontology extraction
- Result aggregation

### Requirements
- Python 3.11+ recommended
- pip
- virtualenv

### Installation
1. Clone the repository
2. Setup Backend and Frontend
	1. Open the `backend/` and `frontend/` folders
	2. For each of them create a virtual environment
	3. For each of them install dependencies
Windows
```bash
cd backend python -m venv venv venv\Scripts\activate
```

Linux / macOS
```shell
cd backend python -m venv venv source venv/bin/activate
```

``` shell
pip install -r requirements.txt
```

3.  Start the Backend
Open the terminal inside `backend/` and run
```bash
uvicorn main:app --reload	
```

The API will be available at: `http://127.0.0.1:8000`

4. Start the Frontend
Open a second terminal inside `frontend/` and activate the frontend virtual environment. Run:
```bash
python app.py
```

The Dash frontend will be available at: `http://127.0.0.1:8050`

#### Testing the backend separately
The backend can be tested separately from the Frontend
`http://127.0.0.1:8000/docs` exposes all available requests. 

An example request body for `evaluate`
```json
{
  "datasets": [
    {
      "dataset_id": "local_file_test",
      "label": "Local Turtle Test",
      "source_config": {
        "type": "rdf_file",
        "file_path": "tests/resources/valid.ttl",
        "format": "turtle"
      }
    },
    {
      "dataset_id": "dbpedia_artworks",
      "label": "DBpedia Artworks",
      "source_config": {
        "type": "sparql_endpoint",
        "endpoint_url": "https://dbpedia.org/sparql",
        "query": "CONSTRUCT { ?s ?p ?o } WHERE { { SELECT DISTINCT ?s WHERE { ?s a <http://dbpedia.org/ontology/Artwork> . } LIMIT 10 } ?s ?p ?o . }"
      }
    }
  ],
  "metrics": [
    {
      "metric_id": "structural_completeness"
    },
    {
      "metric_id": "property_completeness"
    }
  ]
}
```