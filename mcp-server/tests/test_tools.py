"""Read-only tool schema, scope and role boundary tests."""

import sys
from pathlib import Path

import pytest


sys.path.insert(
    0,
    str(
        Path(__file__).parents[1]
        / "src"
    ),
)


from backend_client.mock import MockBackendClient
from schemas.tool_context import (
    GlobalToolRequest,
    PatientToolRequest,
    ToolContext,
)
from tools.registry import (
    GLOBAL_TOOLS,
    PATIENT_TOOLS,
    TOOLS,
    handle,
)


def make_context(
    *,
    actor_role: str = "clinician",
    patient_scope: list[str] | None = None,
) -> ToolContext:
    return ToolContext(
        actor_id="synthetic-actor",
        actor_role=actor_role,
        patient_scope=(
            patient_scope
            if patient_scope is not None
            else ["synthetic-patient"]
        ),
        trace_id="trace-test",
    )


def test_all_tools_are_read_only_getters():
    assert len(PATIENT_TOOLS) == 7
    assert GLOBAL_TOOLS == (
        "get_today_appointments",
        "get_emergency_worklist",
        "get_pending_consultations",
    )
    assert all(
        tool_name.startswith("get_")
        for tool_name in TOOLS
    )


def test_patient_tool_mock_result():
    request = PatientToolRequest(
        context=make_context(),
        patient_id="synthetic-patient",
    )

    result = handle(
        "get_patient_summary",
        request,
        MockBackendClient(),
    )

    assert result.data["is_mock"] is True
    assert result.data["params"] == {
        "patient_id":
            "synthetic-patient",
    }


def test_patient_tool_scope_is_enforced():
    request = PatientToolRequest(
        context=make_context(
            patient_scope=[
                "other-patient",
            ]
        ),
        patient_id="synthetic-patient",
    )

    with pytest.raises(
        PermissionError,
        match="PATIENT_SCOPE_FORBIDDEN",
    ):
        handle(
            "get_patient_summary",
            request,
            MockBackendClient(),
        )


# def test_global_tool_does_not_require_patient_id():
#     request = GlobalToolRequest(
#         context=make_context(
#             patient_scope=[],
#         )
#     )

#     result = handle(
#         "get_today_appointments",
#         request,
#         MockBackendClient(),
#     )

#     assert result.data["is_mock"] is True
#     assert result.data["params"] == {}

@pytest.mark.parametrize(
    "tool_name",
    GLOBAL_TOOLS,
)
def test_global_tool_does_not_require_patient_id(
    tool_name,
):
    request = GlobalToolRequest(
        context=make_context(
            patient_scope=[],
        )
    )

    result = handle(
        tool_name,
        request,
        MockBackendClient(),
    )

    assert result.data["is_mock"] is True
    assert result.data["params"] == {}


# def test_global_tool_is_forbidden_to_patient_role():
#     request = GlobalToolRequest(
#         context=make_context(
#             actor_role="patient",
#             patient_scope=[],
#         )
#     )

#     with pytest.raises(
#         PermissionError,
#         match="GLOBAL_TOOL_FORBIDDEN",
#     ):
#         handle(
#             "get_today_appointments",
#             request,
#             MockBackendClient(),
#         )

@pytest.mark.parametrize(
    "tool_name",
    GLOBAL_TOOLS,
)
def test_global_tool_is_forbidden_to_patient_role(
    tool_name,
):
    request = GlobalToolRequest(
        context=make_context(
            actor_role="patient",
            patient_scope=[],
        )
    )

    with pytest.raises(
        PermissionError,
        match="GLOBAL_TOOL_FORBIDDEN",
    ):
        handle(
            tool_name,
            request,
            MockBackendClient(),
        )