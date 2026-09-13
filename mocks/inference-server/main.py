"""Standalone synthetic inference server; no model or database access."""
import os
from typing import Literal
from uuid import UUID
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
app=FastAPI(title="BrainOn Inference MOCK",version="0.1.0")
@app.get("/health")
def health(): return {"status":"ok","service":"inference-mock","is_mock":True}
@app.get("/ready")
def ready():
    if mock_enabled():
        return {"status": "ready", "mode": "MOCK", "is_mock": True, "model_configured": False}
    raise HTTPException(status_code=503, detail="MOCK_DISABLED")


def mock_enabled():
    return os.getenv("INFERENCE_MOCK_ENABLED", "false").lower() == "true"


class MockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_id: UUID
    outcome: Literal["success", "failure"] = "success"


@app.post("/mock/inference")
def mock_inference(request: MockRequest):
    if not mock_enabled():
        raise HTTPException(status_code=404, detail="MOCK_DISABLED")
    if request.outcome == "failure":
        raise HTTPException(status_code=500, detail="MOCK_INFERENCE_FAILED")
    return {"analysis_id": str(request.analysis_id), "mode": "MOCK", "is_mock": True, "accuracy_simulated": False,
            "status": "SUCCEEDED", "result": {"message": "Synthetic pipeline verification only"}}
