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

        # ======================================================
        # 로그인 사용자 역할 확정
        # ======================================================
        #
        # role / patient_scope는 Client가 결정하지 않는다.
        # JWT 인증이 끝난 request.user를 기준으로 서버가 확정한다.
        # ======================================================

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

        requested_patient_id = context.get(
            "patient_id"
        )

        requested_scope = str(
            context.get(
                "scope",
                "",
            )
        ).strip().upper()

        patient = None

        # ======================================================
        # PATIENT Assistant Scope
        # ======================================================
        #
        # Patient App의 patient_id를 신뢰하지 않는다.
        #
        # JWT request.user
        #   -> Patient.user
        #   -> 로그인한 사용자의 본인 Patient 확정
        #
        # 최종 patient_id / patient_scope는 아래에서
        # 서버가 확정한 Patient로만 구성한다.
        # ======================================================

        if assistant_role == "patient":
            patient = (
                Patient.objects
                .filter(
                    user_id=request.user.id
                )
                .first()
            )

            if patient is None:
                return Response(
                    {
                        "code":
                            "PATIENT_ACCOUNT_NOT_LINKED",
                        "detail":
                            (
                                "로그인 계정과 연결된 "
                                "환자 정보가 없습니다."
                            ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # 정상 Patient App 요청은 patient_id를 보내지 않는다.
            #
            # 호환성을 위해 patient_id가 포함된 요청 자체는 받되,
            # 로그인한 본인의 Patient UUID와 다르면 즉시 차단한다.
            if (
                requested_patient_id is not None
                and requested_patient_id != patient.id
            ):
                return Response(
                    {
                        "code":
                            "PATIENT_CONTEXT_FORBIDDEN",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Patient 역할은 Client가 TODAY/ENCOUNTER 등을 보내도
            # 항상 본인 Patient Context로 고정한다.
            scope = "PATIENT"

        # ======================================================
        # Clinician Assistant Scope
        # ======================================================
        #
        # 기존 임상의 Assistant 동작은 그대로 유지한다.
        #
        # TODAY
        #   -> 특정 환자를 선택하지 않은 상태 허용
        #
        # PATIENT / ENCOUNTER
        #   -> patient_id 필수
        #   -> 기존 can_view_patient() 권한 검사 유지
        # ======================================================

        else:
            scope = requested_scope

            requires_patient = (
                scope
                in {
                    "PATIENT",
                    "ENCOUNTER",
                }
            )

            if (
                requires_patient
                and requested_patient_id is None
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

            if requested_patient_id is not None:
                patient = (
                    Patient.objects
                    .filter(
                        id=requested_patient_id
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

                if not can_view_patient(
                    request.user,
                    patient.id,
                ):
                    return Response(
                        {
                            "code":
                                "PATIENT_CONTEXT_FORBIDDEN",
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
                # Client 요청값이 아니라 서버에서 최종 확정한
                # 실제 Assistant scope를 Audit에 남긴다.
                "scope":
                    scope,

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
