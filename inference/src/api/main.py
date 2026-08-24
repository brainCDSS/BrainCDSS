"""Liveness and readiness API that never pretends an absent model is ready."""
import os
from fastapi import FastAPI
app=FastAPI(title="BrainOn Inference",version="0.1.0")
@app.get("/health")
def health(): return {"status":"ok","service":"inference-api"}
@app.get("/ready")
def ready():
    configured=bool(os.getenv("MODEL_BUNDLE_URI"))
    return {"status":"ready" if configured else "MODEL_NOT_CONFIGURED","model_configured":configured}
