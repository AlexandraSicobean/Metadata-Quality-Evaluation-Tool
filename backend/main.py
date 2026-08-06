"""
main.py
-------
FastAPI application entry point.

Creates the application instance and mounts the evaluation router, which
exposes every endpoint used by the Dash frontend and by any external
client.

Start the server from the backend directory with:

    uvicorn main:app --reload
"""

from fastapi import FastAPI
from api.evaluation_controller import router as evaluation_router

app = FastAPI(
    title="Metadata Quality Evaluation API"
)

app.include_router(evaluation_router)