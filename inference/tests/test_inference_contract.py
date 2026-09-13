from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas import InferenceRequest


def request_payload(analysis_type, roles):
    return {
        "analysis_id": str(uuid4()),
        "analysis_type": analysis_type,
        "attempt": 1,
        "model_selector": {"name": "model", "version": "N00"},
        "inputs": [
            {
                "role": role,
                "uri": f"gs://brainon-inputs/test/{role}.nii.gz",
                "size_bytes": 10,
                "sha256": "a" * 64,
            }
            for role in roles
        ],
    }


@pytest.mark.parametrize(
    ("analysis_type", "roles"),
    [
        ("HEMORRHAGIC_STROKE_CT", ["CT"]),
        ("ISCHEMIC_STROKE_DWI_ADC", ["DWI", "ADC"]),
        ("CEREBRAL_ANEURYSM_MRA", ["MRA"]),
    ],
)
def test_valid_role_contracts(analysis_type, roles):
    assert InferenceRequest.model_validate(request_payload(analysis_type, roles))


@pytest.mark.parametrize("roles", [["ADC", "DWI"], ["DWI"], ["DWI", "DWI"]])
def test_ischemia_requires_ordered_unique_dwi_adc(roles):
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(request_payload("ISCHEMIC_STROKE_DWI_ADC", roles))


def test_selector_rejects_version_and_alias_together():
    payload = request_payload("HEMORRHAGIC_STROKE_CT", ["CT"])
    payload["model_selector"]["alias"] = "production"
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload)
