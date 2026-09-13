"""Schema-first allowlist of read-only Clinical Tool handlers."""

from schemas.tool_context import ToolRequest, ToolResult


TOOLS = (
    "get_patient_summary",
    "get_appointments",
    "get_current_medications",
    "get_medication_safety_result",
    "get_recent_test_results",
    "get_imaging_analysis_result",
    "get_clinical_record_summary",
)


def handle(
    tool_name: str,
    request: ToolRequest,
    backend,
) -> ToolResult:

    if tool_name not in TOOLS:
        raise ValueError("TOOL_NOT_ALLOWED")

    if request.patient_id not in request.context.patient_scope:
        raise PermissionError("PATIENT_SCOPE_FORBIDDEN")

    payload = backend.get(
        f"/internal/v1/mcp/{tool_name}/",
        request.context.trace_id,
        params={
            "patient_id": request.patient_id,
        },
    )

    return ToolResult(
        status=str(payload.get("status", "OK")),
        is_mock=bool(payload.get("is_mock", False)),
        data=payload.get("data", payload),
    )
