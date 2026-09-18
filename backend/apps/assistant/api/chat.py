"""Authenticated React -> Django -> Assistant Service gateway."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients.models import Patient
from apps.patients.selectors.patients import can_view_patient
from apps.audit.services.audit_event import record_audit_event

CLINICIAN_ROLES = {
    "NURSE",
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
}


class AssistantContextSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(
        choices=[
            "TODAY",
            "PATIENT",
            "ENCOUNTER",
        ],
    )

    patient_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    encounter_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class AssistantMessageSerializer(serializers.Serializer):
    message = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        max_length=4000,
    )

    conversation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    context = AssistantContextSerializer()


def _role_code(user) -> str:
    role = getattr(
        user,
        "role",
        "",
    )

    code = getattr(
        role,
        "code",
        role,
    )

    return str(
        code or ""
    ).strip().upper()


def _assistant_role(
    role_code: str,
) -> str | None:
    if role_code == "PATIENT":
        return "patient"

    if role_code in CLINICIAN_ROLES:
        return "clinician"

    return None


def _trace_id(request) -> str:
    """
    Return the canonical BrainOn request ID.

    CorrelationIdMiddleware is the primary owner of request ID
    creation. Header lookup and UUID generation are fallbacks for
    isolated tests or execution without the middleware.
    """

    candidates = (
        getattr(
            request,
            "request_id",
            None,
        ),
        getattr(
            request,
            "trace_id",
            None,
        ),
        request.headers.get(
            "X-Request-ID"
        ),
        request.headers.get(
            "X-Trace-ID"
        ),
    )

    for candidate in candidates:
        if not candidate:
            continue

        try:
            return str(
                UUID(
                    str(candidate)
                )
            )
        except (
            ValueError,
            TypeError,
            AttributeError,
        ):
            continue

    return str(
        uuid4()
    )


def _assistant_url() -> str:
    base_url = os.getenv(
        "ASSISTANT_SERVICE_URL",
        "http://assistant-service:8200",
    ).rstrip("/")

    return f"{base_url}/chat"


def _call_assistant_service(
    payload: dict,
    request_id: str,
) -> dict:
    request_body = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    upstream_request = Request(
        _assistant_url(),
        data=request_body,
        headers={
            "Content-Type":
                "application/json; charset=utf-8",
            "X-Request-ID":
                request_id,
            "X-Trace-ID":
                request_id,
        },
        method="POST",
    )

    timeout_seconds = float(
        os.getenv(
            "ASSISTANT_SERVICE_TIMEOUT_SECONDS",
            "90",
        )
    )

    with urlopen(
        upstream_request,
        timeout=timeout_seconds,
    ) as upstream_response:
        raw = upstream_response.read()

    return json.loads(
        raw.decode("utf-8")
    )


class AssistantMessageView(APIView):
    """
    Authenticated BrainOn Assistant boundary.

    Browser supplies only the user message and selected
    clinical context.

    actor_id / assistant role / patient_scope are derived
    server-side and are never trusted from the browser.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        serializer = (
            AssistantMessageSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        context = data["context"]

        patient_id = context.get(
            "patient_id"
        )

        scope = str(
            context.get(
                "scope",
                "",
            )
        ).strip().upper()


        # ======================================================
        # Assistant Context 정책
        # ======================================================
        #
        # TODAY
        #   → 특정 환자를 선택하지 않은 상태를 허용한다.
        #
        # PATIENT / ENCOUNTER
        #   → 특정 환자 Context가 필요하다.
        #
        # 즉 모든 질문에서 patient_id를 강제하는 것이 아니라
        # 요청 Context 종류에 따라 환자 필요 여부를 결정한다.
        # ======================================================

        requires_patient = (
            scope
            in {
                "PATIENT",
                "ENCOUNTER",
            }
        )


        if (
            requires_patient
            and patient_id is None
        ):
            return Response(
                {
                    "code":
                        "PATIENT_CONTEXT_REQUIRED",

                    "detail":
                        (
                            "환자 기반 질문은 "
                            "환자를 선택한 후 요청하세요."
                        ),
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        # ======================================================
        # 실제 Patient 확인
        # ======================================================
        #
        # patient_id가 있을 때만 Patient DB를 조회한다.
        #
        # TODAY / Global / 일반 질문
        #   patient_id 없음
        #   → patient = None
        #
        # PATIENT / ENCOUNTER
        #   patient_id 있음
        #   → 실제 Patient 존재 여부 확인
        # ======================================================

        patient = None

        if patient_id is not None:
            patient = (
                Patient.objects
                .filter(
                    id=patient_id
                )
                .first()
            )

            if patient is None:
                return Response(
                    {
                        "code":
                            "PATIENT_NOT_FOUND",
                    },
                    status=(
                        status
                        .HTTP_404_NOT_FOUND
                    ),
                )

            if not can_view_patient(request.user, patient.id):
                return Response(
                    {
                        "code": "PATIENT_CONTEXT_FORBIDDEN",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        role_code = _role_code(
            request.user
        )

        assistant_role = (
            _assistant_role(
                role_code
            )
        )

        if assistant_role is None:
            return Response(
                {
                    "code":
                        "ASSISTANT_ROLE_FORBIDDEN",
                    "role":
                        role_code,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        #
        # PATIENT 역할의 patient-account ownership은
        # 최종 Patient/User 관계 정책 확정 후 연결한다.
        #
        # 현재 임상 Web E2E 대상은
        # NURSE / NEUROLOGIST / NEUROSURGEON /
        # RADIOLOGY이다.
        #
        if assistant_role == "patient":
            return Response(
                {
                    "code":
                        "PATIENT_ASSISTANT_SCOPE_NOT_IMPLEMENTED",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        trace_id = _trace_id(
            request
        )

        upstream_payload = {
            "actor_id":
                str(request.user.id),

            "role":
                assistant_role,

            # 특정 환자가 선택된 경우에만
            # 실제 patient UUID를 전달한다.
            #
            # TODAY / Global / 일반 질문:
            # None
            "patient_id":
                (
                    str(patient.id)
                    if patient is not None
                    else None
                ),

            # Browser가 보낸 patient scope를 신뢰하지 않는다.
            #
            # Patient Context:
            #   [patient UUID]
            #
            # Global / TODAY Context:
            #   []
            "patient_scope":
                (
                    [
                        str(patient.id),
                    ]
                    if patient is not None
                    else []
                ),

            "message":
                data["message"],

            "trace_id":
                trace_id,
        }

        try:
            result = (
                _call_assistant_service(
                    upstream_payload,
                    trace_id,
                )
            )

        except HTTPError as exc:
            upstream_code = None
            upstream_detail = None

            try:
                error_body = json.loads(
                    exc.read()
                    .decode("utf-8")
                )

                upstream_code = (
                    error_body.get(
                        "code"
                    )
                )

                upstream_detail = (
                    error_body.get(
                        "detail"
                    )
                )

            except Exception:
                pass


            # ==================================================
            # 정상적인 Client Context 오류 전달
            # ==================================================
            #
            # Assistant Service가 판단한
            # "환자 Context 부족"은 시스템 장애가 아니다.
            #
            # 따라서 502로 변환하지 않고
            # 원래 의미인 HTTP 400을 유지한다.
            # ==================================================

            if (
                exc.code
                == status.HTTP_400_BAD_REQUEST
                and upstream_code
                == "PATIENT_CONTEXT_REQUIRED"
            ):
                return Response(
                    {
                        "code":
                            "PATIENT_CONTEXT_REQUIRED",

                        "detail":
                            (
                                upstream_detail
                                or
                                "환자 기반 질문은 "
                                "환자를 선택한 후 요청하세요."
                            ),

                        "trace_id":
                            trace_id,
                    },
                    status=(
                        status
                        .HTTP_400_BAD_REQUEST
                    ),
                )


            # ==================================================
            # Patient Scope 권한 오류 전달
            # ==================================================

            if (
                exc.code
                == status.HTTP_403_FORBIDDEN
                and upstream_code
                == "PATIENT_SCOPE_FORBIDDEN"
            ):
                return Response(
                    {
                        "code":
                            "PATIENT_SCOPE_FORBIDDEN",

                        "trace_id":
                            trace_id,
                    },
                    status=(
                        status
                        .HTTP_403_FORBIDDEN
                    ),
                )


            # ==================================================
            # 그 외 실제 Upstream 장애
            # ==================================================

            return Response(
                {
                    "code":
                        "ASSISTANT_UPSTREAM_ERROR",

                    "upstream_status":
                        exc.code,

                    "upstream_code":
                        upstream_code,

                    "trace_id":
                        trace_id,
                },
                status=(
                    status
                    .HTTP_502_BAD_GATEWAY
                ),
            )

        except (
            URLError,
            TimeoutError,
            OSError,
        ):
            return Response(
                {
                    "code":
                        "ASSISTANT_SERVICE_UNAVAILABLE",
                    "trace_id":
                        trace_id,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return Response(
                {
                    "code":
                        "ASSISTANT_RESPONSE_INVALID",
                    "trace_id":
                        trace_id,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        answer = result.get(
            "answer"
        )

        if not isinstance(
            answer,
            str,
        ) or not answer.strip():
            return Response(
                {
                    "code":
                        "ASSISTANT_RESPONSE_INVALID",
                    "trace_id":
                        trace_id,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        conversation_id = (
            data.get(
                "conversation_id"
            )
            or uuid4()
        )

        # ======================================================
        # Assistant Audit
        # ======================================================
        #
        # CorrelationIdMiddleware가 만든 canonical request_id를
        # 그대로 AuditLog.request_id에 저장한다.
        #
        # 사용자 질문 원문은 PHI가 포함될 수 있으므로
        # AuditLog에 저장하지 않는다.
        # ======================================================

        record_audit_event(
            source_service=
                "backend.assistant",

            action=
                "ASSISTANT_MESSAGE",

            resource_type=
                "AssistantConversation",

            outcome=
                "SUCCESS",

            request=
                request,

            resource_id=
                conversation_id,

            patient_id=(
                patient.id
                if patient is not None
                else None
            ),

            after_json={
                "scope":
                    str(
                        context.get(
                            "scope",
                            "",
                        )
                    ),

                "context_sources":
                    result.get(
                        "context_sources",
                        [],
                    ),

                "provider":
                    result.get(
                        "provider"
                    ),

                "model":
                    result.get(
                        "model"
                    ),

                "trace_id":
                    trace_id,
            },
        )

        return Response(
            {
                "conversation_id":
                    str(conversation_id),

                "message_id":
                    str(uuid4()),

                "answer":
                    answer,

                "actions": [],

                "created_at":
                    timezone.now()
                    .isoformat(),

                # Debug/trace metadata.
                # React 계약상 추가 필드는 무시 가능.
                "request_id":
                    trace_id,

                # Backward-compatible alias.
                "trace_id":
                    trace_id,

                "provider":
                    result.get(
                        "provider"
                    ),

                "model":
                    result.get(
                        "model"
                    ),

                "context_sources":
                    result.get(
                        "context_sources",
                        [],
                    ),
            },
            status=status.HTTP_200_OK,
        )
