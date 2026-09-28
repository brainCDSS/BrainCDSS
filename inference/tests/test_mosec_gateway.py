from unittest.mock import Mock, patch

import pytest

from src.api.mosec_client import ROUTES, call_mosec
from src.schemas import AnalysisType, InferenceRequest


@pytest.fixture
def requests_by_type():
    common = {
        "analysis_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "attempt": 1,
        "model_selector": {
            "name": "model", "version": "1", "manifest_uri": "gs://models/manifest.json"
        },
        "trace_id": "trace",
    }
    return {
        AnalysisType.HEMORRHAGIC_STROKE_CT: InferenceRequest.model_validate({
            **common, "analysis_type": "HEMORRHAGIC_STROKE_CT",
            "inputs": [{"role": "CT", "uri": "gs://inputs/ct.nii.gz", "size_bytes": 1, "sha256": "a" * 64}],
        }),
        AnalysisType.ISCHEMIC_STROKE_DWI_ADC: InferenceRequest.model_validate({
            **common, "analysis_type": "ISCHEMIC_STROKE_DWI_ADC",
            "inputs": [
                {"role": "DWI", "uri": "gs://inputs/dwi.nii.gz", "size_bytes": 1, "sha256": "b" * 64},
                {"role": "ADC", "uri": "gs://inputs/adc.nii.gz", "size_bytes": 1, "sha256": "c" * 64},
            ],
        }),
        AnalysisType.CEREBRAL_ANEURYSM_MRA: InferenceRequest.model_validate({
            **common, "analysis_type": "CEREBRAL_ANEURYSM_MRA",
            "inputs": [{"role": "MRA", "uri": "gs://inputs/mra.nii.gz", "size_bytes": 1, "sha256": "d" * 64}],
        }),
    }


def test_each_analysis_type_has_a_dedicated_mosec_route():
    assert ROUTES == {
        AnalysisType.HEMORRHAGIC_STROKE_CT: "/v1/models/hemorrhage",
        AnalysisType.ISCHEMIC_STROKE_DWI_ADC: "/v1/models/ischemia",
        AnalysisType.CEREBRAL_ANEURYSM_MRA: "/v1/models/aneurysm",
    }


@patch("src.api.mosec_client.httpx.post")
def test_gateway_routes_requests_without_changing_contract(send, requests_by_type):
    for analysis_type, request in requests_by_type.items():
        response = Mock()
        response.json.return_value = {
            "analysis_id": str(request.analysis_id),
            "analysis_type": analysis_type.value,
            "attempt": 1,
            "status": "FAILED",
            "model": None,
            "outputs": [], "metrics": {}, "timing_ms": {},
            "error": {"code": "TEST", "message": "test", "retryable": False, "detail": {}},
            "trace_id": "trace",
        }
        send.return_value = response
        result = call_mosec(request)
        assert result.analysis_type == analysis_type
        assert send.call_args.args[0].endswith(ROUTES[analysis_type])
