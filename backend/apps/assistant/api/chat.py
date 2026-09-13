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
    candidate = (
        request.headers.get(
            "X-Request-ID",
            "",
        ).strip()
    )

    if candidate:
        try:
            return str(
                UUID(candidate)
            )
        except ValueError:
            pass

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

        # 현재 assistant-service는 patient-specific
        # clinical context를 필수로 요구한다.
        if patient_id is None:
            return Response(
                {
                    "code":
                        "PATIENT_CONTEXT_REQUIRED",
                    "detail":
                        "환자를 선택한 후 다시 요청하세요.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient = (
            Patient.objects
            .filter(id=patient_id)
            .first()
        )

        if patient is None:
            return Response(
                {
                    "code":
                        "PATIENT_NOT_FOUND",
                },
                status=status.HTTP_404_NOT_FOUND,
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

            "patient_id":
                str(patient.id),

            # 브라우저 값을 신뢰하지 않고
            # Django가 직접 scope를 만든다.
            "patient_scope": [
                str(patient.id),
            ],

            "message":
                data["message"],

            "trace_id":
                trace_id,
        }

        try:
            result = (
                _call_assistant_service(
                    upstream_payload
                )
            )

        except HTTPError as exc:
            upstream_code = None

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

            except Exception:
                pass

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
                status=status.HTTP_502_BAD_GATEWAY,
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
                "trace_id":
                    result.get(
                        "trace_id",
                        trace_id,
                    ),

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
