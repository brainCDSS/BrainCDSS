"""BrainOn read-only Clinical MCP server."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from dotenv import load_dotenv


# ============================================================
# mcp-server/src 를 Python import root 로 사용
# ============================================================
# server.py는:
#
# mcp-server/src/server/server.py
#
# 위치에 있으므로 parents[1]은:
#
# mcp-server/src
#
# 가 된다.
#
# backend_client, schemas, tools 등을
#
# from schemas.tool_context import ...
#
# 형태로 import할 수 있도록 src 경로를 sys.path에 추가한다.
# ============================================================

SRC_DIR = Path(__file__).resolve().parents[1]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_DIR),
    )


# ============================================================
# BrainOn MCP 내부 모듈
# ============================================================

from backend_client.mock import MockBackendClient
from backend_client.http import HttpBackendClient

from schemas.tool_context import (
    GlobalToolRequest,
    PatientToolRequest,
    ToolContext,
)

from tools.registry import handle


# ============================================================
# MCP Server 환경변수 로드
# ============================================================
# SERVICE_DIR:
#
# mcp-server/
#
# 를 의미한다.
#
# 로컬 단독 실행 시 mcp-server/.env가 존재하면 읽는다.
# Docker Compose에서는 환경변수가 이미 주입되므로
# override=False를 유지한다.
# ============================================================

SERVICE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(
    SERVICE_DIR / ".env",
    override=False,
)


# ============================================================
# Django Backend Client 생성
# ============================================================
# MCP Server는 PostgreSQL에 직접 접근하지 않는다.
#
# 실제 환경:
#
# MCP
#   ↓ HTTP
# Django Internal API
#   ↓ ORM
# Database
#
# BACKEND_URL + MCP_BACKEND_TOKEN이 모두 있으면
# 실제 Django Backend를 호출한다.
#
# 둘 중 하나라도 없으면 MockBackendClient를 사용한다.
# ============================================================

def build_backend():
    base_url = os.getenv(
        "BACKEND_URL",
        "",
    ).strip()

    token = os.getenv(
        "MCP_BACKEND_TOKEN",
        "",
    ).strip()

    if base_url and token:
        return HttpBackendClient(
            base_url=base_url,
            token=token,
        )

    return MockBackendClient()


# ============================================================
# MCP Server / Backend Client 초기화
# ============================================================

mcp = MCPServer(
    "brainon-clinical-tools"
)

backend = build_backend()


# ============================================================
# 공통 ToolContext 생성
# ============================================================
# Patient Tool과 Global Tool 모두 아래 정보는 공통으로 사용한다.
#
# actor_id
#   → 누가 Assistant를 사용하고 있는지
#
# actor_role
#   → 사용자의 역할
#
# patient_scope
#   → 현재 사용자가 접근 가능한 환자 범위
#
# trace_id
#   → Django → Assistant → MCP → Django 요청을
#      하나의 요청 흐름으로 추적하기 위한 ID
#
# Patient / Global의 차이는 patient_id 존재 여부이므로
# 공통 Context 생성만 별도 함수로 분리한다.
# ============================================================

def _build_context(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
) -> ToolContext:
    return ToolContext(
        actor_id=actor_id,
        actor_role=actor_role,
        patient_scope=patient_scope,
        trace_id=trace_id,
    )


# ============================================================
# Patient Tool 공통 호출 함수
# ============================================================
# 특정 환자 한 명을 조회하는 MCP Tool에서 사용한다.
#
# 예:
#
# get_patient_summary
# get_appointments
# get_current_medications
# get_medication_safety_result
# get_recent_test_results
# get_imaging_analysis_result
# get_clinical_record_summary
#
# Patient Tool은 반드시 patient_id가 존재해야 한다.
#
# 실제 patient_scope 검사는 여기서 하지 않고
# tools/registry.py의 handle()에서 수행한다.
#
# 흐름:
#
# MCP Tool
#   ↓
# _call_patient()
#   ↓
# PatientToolRequest
#   ↓
# registry.handle()
#   ↓
# patient_scope 검사
#   ↓
# Django Internal API
# ============================================================

def _call_patient(
    tool_name: str,
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:

    request = PatientToolRequest(
        context=_build_context(
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


# ============================================================
# Global Tool 공통 호출 함수
# ============================================================
# 특정 환자 한 명을 선택하지 않고
# 업무 전체 현황을 조회하는 MCP Tool에서 사용한다.
#
# 예:
#
# get_today_appointments
# 이후:
# get_emergency_worklist
# get_pending_consultations
#
# Global Tool은 특정 patient_id를 받지 않는다.
#
# 따라서 PatientToolRequest가 아니라
# GlobalToolRequest를 생성한다.
#
# 주의:
# patient_scope 자체를 없애는 것이 아니다.
#
# ToolContext에는 기존 보안/추적 Context를 계속 전달한다.
# 다만 특정 patient_id와 patient_scope를 비교하는 검사는
# Global Tool에서는 수행하지 않는다.
#
# Global Tool의 역할 권한 검사는
# tools/registry.py의 handle()에서 수행한다.
#
# 흐름:
#
# MCP Tool
#   ↓
# _call_global()
#   ↓
# GlobalToolRequest
#   ↓
# registry.handle()
#   ↓
# role 권한 검사
#   ↓
# Django Global Internal API
# ============================================================

def _call_global(
    tool_name: str,
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
) -> dict[str, Any]:

    request = GlobalToolRequest(
        context=_build_context(
            actor_id=actor_id,
            actor_role=actor_role,
            patient_scope=patient_scope,
            trace_id=trace_id,
        ),
    )

    return handle(
        tool_name,
        request,
        backend,
    ).model_dump()


# ============================================================
# PATIENT TOOL 1
# 환자 기본 요약
# ============================================================

@mcp.tool()
def get_patient_summary(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only patient summary."""

    return _call_patient(
        "get_patient_summary",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


# ============================================================
# PATIENT TOOL 2
# 특정 환자의 예약 정보
# ============================================================
# 기존 get_appointments는 그대로 유지한다.
#
# 의미:
# "이 환자의 예약 알려줘"
#
# 새로 추가할 get_today_appointments와 역할이 다르다.
# ============================================================

@mcp.tool()
def get_appointments(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only appointment information."""

    return _call_patient(
        "get_appointments",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


# ============================================================
# PATIENT TOOL 3
# 현재 처방 약물
# ============================================================

@mcp.tool()
def get_current_medications(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only current medication information."""

    return _call_patient(
        "get_current_medications",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


# ============================================================
# PATIENT TOOL 4
# Medication Safety 결과
# ============================================================

@mcp.tool()
def get_medication_safety_result(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only medication safety result."""

    return _call_patient(
        "get_medication_safety_result",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


# ============================================================
# PATIENT TOOL 5
# 최근 검사 결과
# ============================================================

@mcp.tool()
def get_recent_test_results(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only recent test results."""

    return _call_patient(
        "get_recent_test_results",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


# ============================================================
# PATIENT TOOL 6
# 영상 / AI 분석 결과
# ============================================================

@mcp.tool()
def get_imaging_analysis_result(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only imaging and AI analysis result."""

    return _call_patient(
        "get_imaging_analysis_result",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


# ============================================================
# PATIENT TOOL 7
# 임상기록 요약
# ============================================================

@mcp.tool()
def get_clinical_record_summary(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
    patient_id: str,
) -> dict[str, Any]:
    """Read-only clinical record summary."""

    return _call_patient(
        "get_clinical_record_summary",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
        patient_id,
    )


# ============================================================
# GLOBAL TOOL 1
# 오늘 전체 예약 현황
# ============================================================
# 이번 36-C에서 새로 추가하는 첫 Global Tool이다.
#
# 중요한 차이:
#
# get_appointments
#   → 특정 환자 예약
#   → patient_id 필요
#
# get_today_appointments
#   → 오늘 전체 예약 현황
#   → patient_id 없음
#
# 이 함수는 아직 DB를 직접 조회하지 않는다.
#
# 흐름:
#
# get_today_appointments
#   ↓
# _call_global()
#   ↓
# registry.handle()
#   ↓
# /internal/v1/mcp/get_today_appointments/
#   ↓
# Django ORM
#   ↓
# Appointment
#
# 실제 Django 조회 API는 36-D에서 연결한다.
# ============================================================

@mcp.tool()
def get_today_appointments(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
) -> dict[str, Any]:
    """Read-only today's appointment worklist."""

    return _call_global(
        "get_today_appointments",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
    )

# ============================================================
# GLOBAL TOOL 2
# 현재 응급환자 Worklist
# ============================================================
# 특정 환자 한 명의 데이터를 조회하는 Patient Tool이 아니라
# 현재 응급업무 전체 현황을 조회하는 Global Tool이다.
#
# patient_id를 받지 않는다.
# Global Tool 사용 권한은 registry.py에서 검사한다.
#
# 흐름:
#
# Assistant Service
#     ↓
# get_emergency_worklist
#     ↓
# _call_global()
#     ↓
# registry.handle()
#     ↓
# Django Internal API
#     ↓
# EmergencyEvent 실제 DB 조회
# ============================================================

@mcp.tool()
def get_emergency_worklist(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
) -> dict[str, Any]:
    """Read-only current emergency worklist."""

    return _call_global(
        "get_emergency_worklist",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
    )


# ============================================================
# GLOBAL TOOL 3
# 처리 대기 중 협진 Worklist
# ============================================================
# 특정 환자 한 명의 협진 내역이 아니라
# 현재 처리 대기/진행 중인 전체 협진 현황을 조회한다.
#
# patient_id를 받지 않는다.
# Global Tool 사용 권한은 registry.py에서 검사한다.
# ============================================================

@mcp.tool()
def get_pending_consultations(
    actor_id: str,
    actor_role: str,
    patient_scope: list[str],
    trace_id: str,
) -> dict[str, Any]:
    """Read-only pending consultation worklist."""

    return _call_global(
        "get_pending_consultations",
        actor_id,
        actor_role,
        patient_scope,
        trace_id,
    )

# ============================================================
# MCP Server 실행
# ============================================================
# 기존 실행 구조는 변경하지 않는다.
#
# Docker Compose 환경:
# MCP_HOST=0.0.0.0
# PORT=8300
#
# Streamable HTTP endpoint:
#
# http://mcp-server:8300/mcp
# ============================================================

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv(
            "MCP_HOST",
            "127.0.0.1",
        ),
        port=int(
            os.getenv(
                "PORT",
                "8300",
            )
        ),
        streamable_http_path="/mcp",
        json_response=True,
    )