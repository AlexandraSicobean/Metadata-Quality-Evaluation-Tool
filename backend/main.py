from fastapi import FastAPI
from api.evaluation_controller import router as evaluation_router

app = FastAPI(
    title="Metadata Quality Evaluation API"
)

app.include_router(evaluation_router)