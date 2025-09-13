import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from src.api.webhooks import router as webhooks_router
from src.api.telegram import router as telegram_router
from src.api.ops import router as ops_router
from src.api.rfp import router as rfp_router
from src.graph.workflow import app as workflow_app

app = FastAPI()

app.include_router(webhooks_router)
app.include_router(telegram_router)
app.include_router(ops_router)
app.include_router(rfp_router)
app.state.workflow = workflow_app

@app.post("/invoke")
async def invoke(request: dict):
    inputs = {"initial_query": request.get("message")}
    return app.state.workflow.invoke(inputs)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "Welcome to the Ritveer API"}
