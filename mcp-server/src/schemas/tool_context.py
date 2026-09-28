"""Every read-only tool carries identity scope and audit context."""

from pydantic import BaseModel, Field


class ToolContext(BaseModel):
    actor_id: str
    actor_role: str
    patient_scope: list[str]
    trace_id: str


class PatientToolRequest(BaseModel):
    """Request contract for patient-scoped tools."""

    context: ToolContext
    patient_id: str


class GlobalToolRequest(BaseModel):
    """Request contract for non-patient-specific global tools."""

    context: ToolContext


# Temporary compatibility for the current server.py.
# server.py를 Patient / Global 호출로 분리한 뒤 제거 (분리 하지 않는다면 사용)
# ToolRequest = PatientToolRequest


class ToolResult(BaseModel):
    status: str = "NOT_IMPLEMENTED"
    is_mock: bool = True
    data: dict = Field(default_factory=dict)