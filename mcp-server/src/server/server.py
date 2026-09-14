"""BrainOn read-only Clinical MCP server."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from dotenv import load_dotenv


# mcp-server/src 를 import root 로 사용한다.
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend_client.mock import MockBackendClient
from backend_client.http import HttpBackendClient
from schemas.tool_context import ToolContext, ToolRequest
from tools.registry import handle


SERVICE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(SERVICE_DIR / ".env", override=False)


def build_backend():
    base_url = os.getenv("BACKEND_URL", "").strip()
    token = os.getenv("MCP_BACKEND_TOKEN", "").strip()

    if base_url and token:
        return HttpBackendClient(
            base_url=base_url,
            token=token,
        )

    return MockBackendClient()


mcp = MCPServer("brainon-clinical-tools")
backend = build_backend()


def _call(
    tool_name: str,
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    request = ToolRequest(
        context=ToolContext(
            actor_id=actor_id,
            actor_role=actor_role,
            patient_scope=patient_scope,
            trace_id=trace_id,
        ),
        patient_id=patient_id,
    )

    return handle(
        tool_name,
        request,
        backend,
    ).model_dump()


@mcp.tool()
def get_patient_summary(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only patient summary."""
    return _call(
        "get_patient_summary",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


@mcp.tool()
def get_appointments(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only appointment information."""
    return _call(
        "get_appointments",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


@mcp.tool()
def get_current_medications(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only current medication information."""
    return _call(
        "get_current_medications",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


@mcp.tool()
def get_medication_safety_result(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only medication safety result."""
    return _call(
        "get_medication_safety_result",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


@mcp.tool()
def get_recent_test_results(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only recent test results."""
    return _call(
        "get_recent_test_results",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


@mcp.tool()
def get_imaging_analysis_result(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only imaging and AI analysis result."""
    return _call(
        "get_imaging_analysis_result",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


@mcp.tool()
def get_clinical_record_summary(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only clinical record summary."""
    return _call(
        "get_clinical_record_summary",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8300")),
        streamable_http_path="/mcp",
        json_response=True,
    )
