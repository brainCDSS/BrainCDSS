"""Authenticated Cloud Run entrypoint for BrainOn GPU inference."""

from __future__ import annotations

import os
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.errors import InferenceServiceError
from src.api.mosec_client import call_mosec, mosec_readiness
from src.runtime import get_service
from src.schemas import InferenceError, InferenceRequest, InferenceResponse

app = FastAPI(title="BrainOn Inference", version="1.0.0")


@app.exception_handler(RequestValidationError)
async def invalid_request_handler(_request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": "request does not match the inference contract",
                "retryable": False,
                "detail": {"validation": jsonable_encoder(exc.errors())},
            }
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "brainon-inference"}


@app.get("/ready")
def ready():
    missing = [name for name in ("GCS_MODEL_BUCKET", "GCS_RESULT_BUCKET") if not os.getenv(name)]
    if missing:
        return {
            "status": "MODEL_NOT_CONFIGURED",
            "ready": False,
            "reasons": [f"MISSING_ENV:{name}" for name in missing],
        }
    try:
        state = (
            mosec_readiness()
            if os.getenv("MODEL_SERVING_BACKEND", "direct") == "mosec"
            else get_service().readiness()
        )
    except Exception as exc:
        state = {"ready": False, "reasons": [f"INITIALIZATION_FAILED:{type(exc).__name__}"]}
    return {"status": "ready" if state["ready"] else "not_ready", **state}


@app.post("/v1/inferences", response_model=InferenceResponse)
def create_inference(request: InferenceRequest):
    trace_id = request.trace_id or str(uuid4())
    try:
        routed_request = request.model_copy(update={"trace_id": trace_id})
        if os.getenv("MODEL_SERVING_BACKEND", "direct") == "mosec":
            return call_mosec(routed_request)
        return get_service().execute(routed_request)
    except InferenceServiceError as exc:
        return InferenceResponse(
            analysis_id=request.analysis_id,
            analysis_type=request.analysis_type,
            attempt=request.attempt,
            status="FAILED",
            outputs=[],
            metrics={},
            timing_ms={},
            error=InferenceError(
                code=exc.code,
                message=str(exc),
                retryable=exc.retryable,
                detail=exc.detail,
            ),
            trace_id=trace_id,
        )
    except Exception:
        return InferenceResponse(
            analysis_id=request.analysis_id,
            analysis_type=request.analysis_type,
            attempt=request.attempt,
            status="FAILED",
            outputs=[],
            metrics={},
            timing_ms={},
            error=InferenceError(
                code="INTERNAL_ERROR",
                message="unexpected inference service failure",
                retryable=False,
            ),
            trace_id=trace_id,
        )
