from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.remaining149_runtime import ContractConflict
from apps.consultations.models import Consultation, ConsultationChatPresence, ConsultationMessage
from apps.organizations.models import Clinician
from apps.notifications.services.consultation_messages import (
    create_consultation_message_notification,
)


MESSAGE_MAX_LENGTH = 2000
MESSAGE_PAGE_SIZE = 100
WRITABLE_STATUSES = {"REQUESTED", "ACCEPTED", "IN_PROGRESS"}
PRESENCE_ACTIVE_FOR = timedelta(seconds=30)
TYPING_ACTIVE_FOR = timedelta(seconds=5)


def _participant_consultation(consultation_id, user):
    try:
        consultation = Consultation.objects.only(
            "id",
            "requested_by_id",
            "assigned_to_id",
            "status",
        ).get(pk=consultation_id)
    except Consultation.DoesNotExist as exc:
        raise NotFound({"code": "CONSULTATION_NOT_FOUND"}) from exc

    if user.id not in {
        consultation.requested_by_id,
        consultation.assigned_to_id,
    }:
        raise PermissionDenied({
            "code": "CONSULTATION_MESSAGE_FORBIDDEN",
            "detail": "Only consultation participants can access messages.",
        })
    return consultation


def _serialize_messages(messages, current_user):
    sender_ids = {message.sender_id for message in messages}
    clinicians = {
        clinician.user_id: clinician
        for clinician in Clinician.objects.filter(
            user_id__in=sender_ids,
        ).select_related("department")
    }

    return [
        {
            "message_id": str(message.id),
            "consultation_id": str(message.consultation_id),
            "sender": {
                "id": str(message.sender_id),
                "name": message.sender.name,
                "department": (
                    clinicians[message.sender_id].department.name
                    if message.sender_id in clinicians
                    else None
                ),
            },
            "content": message.content,
            "created_at": message.created_at,
            "is_mine": message.sender_id == current_user.id,
        }
        for message in messages
    ]


def _presence_payload(consultation, current_user):
    participant_ids = [consultation.requested_by_id]
    if consultation.assigned_to_id and consultation.assigned_to_id not in participant_ids:
        participant_ids.append(consultation.assigned_to_id)
    now = timezone.now()
    presences = {item.user_id: item for item in ConsultationChatPresence.objects.filter(consultation=consultation, user_id__in=participant_ids)}
    clinicians = {item.user_id: item for item in Clinician.objects.filter(user_id__in=participant_ids).select_related("user", "department")}
    participants = []
    for user_id in participant_ids:
        clinician = clinicians.get(user_id)
        presence = presences.get(user_id)
        online = bool(presence and presence.last_seen_at >= now - PRESENCE_ACTIVE_FOR)
        typing = bool(online and presence and presence.is_typing and presence.typing_updated_at and presence.typing_updated_at >= now - TYPING_ACTIVE_FOR)
        participants.append({"id": str(user_id), "name": clinician.user.name if clinician else "Unknown", "department": clinician.department.name if clinician else None, "is_online": online, "is_typing": typing, "is_mine": user_id == current_user.id})
    return {"participant_count": len(participants), "active_count": sum(item["is_online"] for item in participants), "participants": participants}


class ConsultationMessageCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, consultation_id):
        consultation = _participant_consultation(consultation_id, request.user)
        queryset = ConsultationMessage.objects.filter(
            consultation=consultation,
        ).select_related("sender")

        after = request.query_params.get("after")
        if after:
            try:
                marker = ConsultationMessage.objects.only(
                    "id",
                    "created_at",
                ).get(consultation=consultation, pk=after)
            except (ConsultationMessage.DoesNotExist, ValueError) as exc:
                raise ValidationError({
                    "code": "CONSULTATION_MESSAGE_CURSOR_INVALID",
                    "detail": "The message cursor is invalid.",
                }) from exc
            queryset = queryset.filter(
                Q(created_at__gt=marker.created_at)
                | Q(created_at=marker.created_at, id__gt=marker.id)
            ).order_by("created_at", "id")
            messages = list(queryset[: MESSAGE_PAGE_SIZE + 1])
        else:
            newest_first = list(
                queryset.order_by("-created_at", "-id")[:MESSAGE_PAGE_SIZE]
            )
            messages = list(reversed(newest_first))

        has_more = bool(after) and len(messages) > MESSAGE_PAGE_SIZE
        if len(messages) > MESSAGE_PAGE_SIZE:
            messages = messages[:MESSAGE_PAGE_SIZE]
        next_cursor = str(messages[-1].id) if messages else after

        return Response({
            "results": _serialize_messages(messages, request.user),
            "next_cursor": next_cursor,
            "has_more": has_more,
            "presence": _presence_payload(consultation, request.user),
        })

    def post(self, request, consultation_id):
        consultation = _participant_consultation(consultation_id, request.user)
        if consultation.status not in WRITABLE_STATUSES:
            raise ContractConflict({
                "code": "CONSULTATION_MESSAGE_CLOSED",
                "detail": "Messages cannot be sent after the consultation is closed.",
            })

        if not isinstance(request.data, dict):
            raise ValidationError({
                "code": "VALIDATION_ERROR",
                "detail": "JSON object is required.",
            })
        content = request.data.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValidationError({
                "code": "CONSULTATION_MESSAGE_REQUIRED",
                "detail": "Message content is required.",
            })
        content = content.strip()
        if len(content) > MESSAGE_MAX_LENGTH:
            raise ValidationError({
                "code": "CONSULTATION_MESSAGE_TOO_LONG",
                "detail": f"Message content must be {MESSAGE_MAX_LENGTH} characters or fewer.",
            })

        with transaction.atomic():
            message = ConsultationMessage.objects.create(
                consultation=consultation,
                sender=request.user,
                content=content,
            )

            recipient_id = (
                consultation.assigned_to_id
                if consultation.requested_by_id
                == request.user.id
                else consultation.requested_by_id
            )

            notification = None

            if recipient_id is not None:
                from apps.accounts.models import User

                recipient = User.objects.get(
                    pk=recipient_id,
                )

                notification = (
                    create_consultation_message_notification(
                        consultation=consultation,
                        message=message,
                        recipient=recipient,
                    )
                )


        payload = _serialize_messages(
            [message],
            request.user,
        )[0]

        return Response(
            payload,
            status=201,
        )


class ConsultationMessagePresenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, consultation_id):
        consultation = _participant_consultation(
            consultation_id,
            request.user,
        )

        return Response(
            _presence_payload(
                consultation,
                request.user,
            )
        )

    def put(self, request, consultation_id):
        consultation = _participant_consultation(
            consultation_id,
            request.user,
        )

        if (
            not isinstance(request.data, dict)
            or not isinstance(request.data.get("is_typing"), bool)
        ):
            raise ValidationError({
                "code": "CONSULTATION_PRESENCE_INVALID",
                "detail": "is_typing must be a boolean.",
            })

        now = timezone.now()
        is_typing = request.data["is_typing"]

        ConsultationChatPresence.objects.update_or_create(
            consultation=consultation,
            user=request.user,
            defaults={
                "last_seen_at": now,
                "is_typing": is_typing,
                "typing_updated_at": now if is_typing else None,
            },
        )

        return Response(
            _presence_payload(
                consultation,
                request.user,
            )
        )