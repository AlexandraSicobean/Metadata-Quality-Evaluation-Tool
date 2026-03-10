from fastapi import FastAPI
from api.evaluation_controller import router as evaluation_router
from rdflib.namespace import XSD
import rdflib.term

rdflib.term._toPythonMapping.pop(XSD.hexBinary, None)

app = FastAPI(
    title="Metadata Quality Evaluation API"
)

app.include_router(evaluation_router)