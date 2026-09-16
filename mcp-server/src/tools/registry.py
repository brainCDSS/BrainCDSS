"""Schema-first allowlist of read-only Clinical Tool handlers."""

from schemas.tool_context import (
    GlobalToolRequest,
    PatientToolRequest,
    ToolResult,
)


PATIENT_TOOLS = (
    "get_patient_summary",
    "get_appointments",
    "get_current_medications",
    "get_medication_safety_result",
    "get_recent_test_results",
    "get_imaging_analysis_result",
    "get_clinical_record_summary",
)


# Global Tool은 실제 구현되는 순서대로 추가한다.
GLOBAL_TOOLS = (
    "get_today_appointments",
    "get_emergency_worklist",
    "get_pending_consultations",
)

TOOLS = PATIENT_TOOLS + GLOBAL_TOOLS


# 현재 Assistant Gateway가 임상 역할을
# patient / clinician 두 종류로 변환해 전달한다.
GLOBAL_ALLOWED_ROLES = frozenset(
    {
        "clinician",
    }
)


def handle(
    tool_name: str,
    request: PatientToolRequest | GlobalToolRequest,
    backend,
) -> ToolResult:

    if tool_name in PATIENT_TOOLS:
        if not isinstance(
            request,
            PatientToolRequest,
        ):
            raise ValueError(
                "PATIENT_CONTEXT_REQUIRED"
            )

        if (
            request.patient_id
            not in request.context.patient_scope
        ):
            raise PermissionError(
                "PATIENT_SCOPE_FORBIDDEN"
            )

        params = {
            "patient_id": request.patient_id,
        }

    elif tool_name in GLOBAL_TOOLS:
        if not isinstance(
            request,
            GlobalToolRequest,
        ):
            raise ValueError(
                "GLOBAL_CONTEXT_REQUIRED"
            )

        actor_role = (
            request.context.actor_role
            .strip()
            .lower()
        )

        if (
            actor_role
            not in GLOBAL_ALLOWED_ROLES
        ):
            raise PermissionError(
                "GLOBAL_TOOL_FORBIDDEN"
            )

        # Global Tool에는 특정 patient_id를 전달하지 않는다.
        params = {}

    else:
        raise ValueError(
            "TOOL_NOT_ALLOWED"
        )

    payload = backend.get(
        f"/internal/v1/mcp/{tool_name}/",
        request.context.trace_id,
        params=params,
        actor_id=
            request.context.actor_id,
        actor_role=
            request.context.actor_role,
    )

    return ToolResult(
        status=str(
            payload.get(
                "status",
                "OK",
            )
        ),
        is_mock=bool(
            payload.get(
                "is_mock",
                False,
            )
        ),
        data=payload.get(
            "data",
            payload,
        ),
    )