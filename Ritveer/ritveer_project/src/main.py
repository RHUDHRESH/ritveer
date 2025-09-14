import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .api.webhooks import router as webhooks_router
# from .api.telegram import router as telegram_router  # TODO: Implement
# from .api.ops import router as ops_router  # TODO: Implement
from .api.rfp import router as rfp_router
from .api.pay import router as pay_router
from .api.cash import router as cash_router
from .api.events import router as events_router
from .api.admin import router as admin_router
from .api.price import router as price_router
from .api.learn import router as learn_router
from .api.metrics import router as metrics_router
from .api.catalog import router as catalog_router
from .api.catalog_share import router as catalog_share_router
from .api.suppliers import router as suppliers_router
from .api.research import router as research_router
from .state.store import reset_state
# from .api.suppliers import router as suppliers_router  # TODO: Implement
from src.tools.policy import policy as policy_store, env_overrides
from .tools.scheduler import start as start_scheduler
from .jobs.events_refresh import refresh_events
# from src.graph.workflow import app as workflow_app  # TODO: Fix imports

app = FastAPI(title="Ritveer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/exports", StaticFiles(directory="./exports"), name="exports")

app.include_router(webhooks_router)
# app.include_router(telegram_router)  # TODO: Implement
# app.include_router(ops_router)  # TODO: Implement
app.include_router(rfp_router)
app.include_router(pay_router)
app.include_router(cash_router)
app.include_router(events_router)
app.include_router(admin_router)
app.include_router(price_router)
app.include_router(learn_router)
app.include_router(metrics_router)
app.include_router(catalog_router)
app.include_router(catalog_share_router)
app.include_router(suppliers_router)
app.include_router(research_router)
# app.state.workflow = workflow_app  # TODO: Fix imports

@app.post("/invoke")
async def invoke(request: dict):
    inputs = {"initial_query": request.get("message")}
    return app.state.workflow.invoke(inputs)

@app.get("/policy")
def get_policy():
    return policy_store.dict()

@app.post("/policy/reload")
def reload_policy():
    ok, err = policy_store.reload()
    if not ok:
        raise HTTPException(status_code=400, detail={"error": "validation_failed", "details": err})
    return {"ok": True}

@app.on_event("startup")
async def _boot_jobs():
    # run refresh once a day
    start_scheduler(app, tasks=[(24*3600, refresh_events)])

@app.get("/policy/raw")
def get_policy_raw():
    return policy_store.raw()

@app.get("/policy/overrides")
def get_policy_overrides():
    return env_overrides()

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "Welcome to the Ritveer API"}

@app.post("/reset/{cid}")
def reset(cid: str):
    reset_state(cid)
    return {"ok": True, "message": f"State reset for {cid}"}
