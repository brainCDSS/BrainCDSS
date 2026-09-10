from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from src.api import main
from src.schemas import AnalysisType, InferenceResponse, ModelInfo, OutputObject

client = TestClient(main.app)


class FakeService:
    def execute(self, request):
        return InferenceResponse(
            analysis_id=request.analysis_id,
            analysis_type=request.analysis_type,
            attempt=request.attempt,
            status="SUCCEEDED",
            model=ModelInfo(
                name="hemorrhagic-stroke-ct",
                version="H-N00",
                manifest_uri="gs://brainon-cdss-models/hemorrhagic-stroke-ct/H-N00/manifest.json",
            ),
            outputs=[
                OutputObject(
                    type="NIFTI_MASK", uri="gs://results/mask.nii.gz", size_bytes=1, sha256="a" * 64
                ),
                OutputObject(
                    type="RESULT_JSON", uri="gs://results/result.json", size_bytes=1, sha256="b" * 64
                ),
            ],
            metrics={"lesion_voxels": 1},
            timing_ms={"total": 1.0},
            error=None,
            trace_id=request.trace_id or "trace",
        )


def payload():
    return {
        "analysis_id": str(uuid4()),
        "analysis_type": AnalysisType.HEMORRHAGIC_STROKE_CT,
        "attempt": 1,
        "model_selector": {"name": "hemorrhagic-stroke-ct", "version": "H-N00"},
        "inputs": [
            {
                "role": "CT",
                "uri": "gs://brainon-inputs/a/ct.nii.gz",
                "size_bytes": 1,
                "sha256": "c" * 64,
            }
        ],
    }


def test_inference_endpoint_uses_real_contract(monkeypatch):
    monkeypatch.setattr(main, "get_service", lambda: FakeService())
    response = client.post("/v1/inferences", json=payload())
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCEEDED"
    assert UUID(response.json()["analysis_id"])


def test_invalid_roles_use_standard_error():
    body = payload()
    body["inputs"][0]["role"] = "ADC"
    response = client.post("/v1/inferences", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
