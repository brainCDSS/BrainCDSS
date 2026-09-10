"""Shared HTTP contract used by the inference control plane."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalysisType(StrEnum):
    HEMORRHAGIC_STROKE_CT = "HEMORRHAGIC_STROKE_CT"
    ISCHEMIC_STROKE_DWI_ADC = "ISCHEMIC_STROKE_DWI_ADC"
    CEREBRAL_ANEURYSM_MRA = "CEREBRAL_ANEURYSM_MRA"


EXPECTED_ROLES = {
    AnalysisType.HEMORRHAGIC_STROKE_CT: ("CT",),
    AnalysisType.ISCHEMIC_STROKE_DWI_ADC: ("DWI", "ADC"),
    AnalysisType.CEREBRAL_ANEURYSM_MRA: ("MRA",),
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelSelector(StrictModel):
    name: str = Field(min_length=1)
    version: str | None = None
    alias: str | None = None
    manifest_uri: str | None = Field(default=None, pattern=r"^gs://")

    @model_validator(mode="after")
    def select_exactly_one_version_source(self):
        if bool(self.version) == bool(self.alias):
            raise ValueError("exactly one of version or alias is required")
        return self


class InputObject(StrictModel):
    role: Literal["CT", "DWI", "ADC", "MRA"]
    uri: str = Field(pattern=r"^gs://")
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class InferenceRequest(StrictModel):
    analysis_id: UUID
    analysis_type: AnalysisType
    attempt: int = Field(ge=1)
    model_selector: ModelSelector
    inputs: list[InputObject] = Field(min_length=1, max_length=2)
    trace_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_roles(self):
        roles = tuple(item.role for item in self.inputs)
        if len(set(roles)) != len(roles):
            raise ValueError("duplicate input role")
        expected = EXPECTED_ROLES[self.analysis_type]
        if roles != expected:
            raise ValueError(
                f"input roles for {self.analysis_type.value} must be {list(expected)} in order"
            )
        return self


class ModelInfo(StrictModel):
    name: str
    version: str
    mlflow_run_id: str | None = None
    manifest_uri: str


class OutputObject(StrictModel):
    type: Literal["NIFTI_MASK", "RESULT_JSON"]
    uri: str = Field(pattern=r"^gs://")
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class InferenceError(StrictModel):
    code: str
    message: str
    retryable: bool
    detail: dict[str, Any] = Field(default_factory=dict)


class InferenceResponse(StrictModel):
    analysis_id: UUID
    analysis_type: AnalysisType
    attempt: int
    status: Literal["SUCCEEDED", "FAILED"]
    model: ModelInfo | None = None
    outputs: list[OutputObject] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    timing_ms: dict[str, float] = Field(default_factory=dict)
    error: InferenceError | None = None
    trace_id: str

    @model_validator(mode="after")
    def validate_status_payload(self):
        if self.status == "SUCCEEDED" and (self.error is not None or len(self.outputs) != 2):
            raise ValueError("successful response requires two outputs and no error")
        if self.status == "FAILED" and self.error is None:
            raise ValueError("failed response requires error")
        return self
