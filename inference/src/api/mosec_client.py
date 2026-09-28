"""Internal client from the FastAPI contract gateway to MOSEC model routes."""

import os

import httpx

from src.schemas import AnalysisType, InferenceRequest, InferenceResponse


ROUTES = {
    AnalysisType.HEMORRHAGIC_STROKE_CT: "/v1/models/hemorrhage",
    AnalysisType.ISCHEMIC_STROKE_DWI_ADC: "/v1/models/ischemia",
    AnalysisType.CEREBRAL_ANEURYSM_MRA: "/v1/models/aneurysm",
}


def call_mosec(request: InferenceRequest) -> InferenceResponse:
    base_url = os.getenv("MOSEC_URL", "http://127.0.0.1:8101").rstrip("/")
    timeout = float(os.getenv("MOSEC_REQUEST_TIMEOUT_SECONDS", "1800"))
    response = httpx.post(
        base_url + ROUTES[request.analysis_type],
        json=request.model_dump(mode="json"),
        timeout=timeout,
    )
    response.raise_for_status()
    return InferenceResponse.model_validate(response.json())


def mosec_readiness() -> dict:
    base_url = os.getenv("MOSEC_URL", "http://127.0.0.1:8101").rstrip("/")
    try:
        response = httpx.get(base_url + "/metrics", timeout=2)
        response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        return {"ready": False, "reasons": [f"MOSEC_UNAVAILABLE:{type(exc).__name__}"]}
    return {"ready": True, "reasons": []}
