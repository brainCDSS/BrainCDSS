from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.errors import ContractAPIException
from apps.notifications.api.permissions import NotificationAccessPermission
from apps.notifications.models import (
    Notification,
    NotificationCategoryPreference,
    NotificationSetting,
)


DEFAULT_CATEGORIES = (
    "EMERGENCY", "CONSULTATION", "PRESCRIPTION", "MEDICATION",
    "MEDICATION_SAFETY",
    "AI_ANALYSIS", "APPOINTMENT", "SYSTEM", "CRITICAL",
)


def _item(row):
    return {
        "id": str(row.id), "category": row.category, "severity": row.severity,
        "title": row.title, "body": row.body, "data": row.data_json or {},
        "is_read": row.is_read, "read_at": row.read_at,
        "created_at": row.created_at,
    }


def _preferences(user):
    setting = NotificationSetting.objects.filter(user=user).first()
    saved = {
        row.category: row
        for row in NotificationCategoryPreference.objects.filter(user=user)
    }
    categories = []
    for category in DEFAULT_CATEGORIES:
        required = category == "CRITICAL"
        categories.append({
            "category": category,
            "enabled": True if required else saved.get(category, None) is None or saved[category].enabled,
            "required": required,
        })
    return {
        "dnd": {
            "enabled": setting.dnd_enabled if setting else False,
            "start": setting.dnd_start if setting else None,
            "end": setting.dnd_end if setting else None,
            "timezone": setting.timezone if setting else "Asia/Seoul",
        },
        "categories": categories,
        "updated_at": setting.updated_at if setting else None,
    }


class NotificationCollectionView(APIView):
    permission_classes = [NotificationAccessPermission]

    def get(self, request):
        rows = Notification.objects.filter(recipient_user=request.user).order_by("-created_at")
        unread = str(request.query_params.get("unread_only", "")).lower()
        if unread in {"true", "1"}:
            rows = rows.filter(is_read=False)
        category = str(request.query_params.get("category", "")).strip()
        if category:
            rows = rows.filter(category=category)
        try:
            page_number = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            raise ContractAPIException("VALIDATION_ERROR", "page must be an integer.", 400)
        page = Paginator(rows, 20).get_page(page_number)
        return Response({
            "count": page.paginator.count,
            "unread_count": Notification.objects.filter(
                recipient_user=request.user, is_read=False
            ).count(),
            "next": page.next_page_number() if page.has_next() else None,
            "previous": page.previous_page_number() if page.has_previous() else None,
            "results": [_item(row) for row in page.object_list],
        })


class NotificationReadView(APIView):
    permission_classes = [NotificationAccessPermission]

    @transaction.atomic
    def patch(self, request, notification_id):
        row = Notification.objects.select_for_update().filter(
            pk=notification_id, recipient_user=request.user
        ).first()
        if row is None:
            raise ContractAPIException("NOTIFICATION_NOT_FOUND", "Notification was not found.", 404)
        if not row.is_read:
            row.is_read = True
            row.read_at = timezone.now()
            row.save(update_fields=["is_read", "read_at"])
        return Response(_item(row), status=status.HTTP_200_OK)


class NotificationPreferenceView(APIView):
    permission_classes = [NotificationAccessPermission]

    def get(self, request):
        return Response(_preferences(request.user))

    @transaction.atomic
    def patch(self, request):
        dnd_enabled = bool(request.data.get("dnd_enabled", False))
        dnd_start = request.data.get("dnd_start") or None
        dnd_end = request.data.get("dnd_end") or None
        timezone_name = str(request.data.get("timezone") or "Asia/Seoul")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            raise ContractAPIException("VALIDATION_ERROR", "Unknown timezone.", 400)
        if dnd_enabled and (not dnd_start or not dnd_end):
            raise ContractAPIException(
                "NOTIFICATION_POLICY_VIOLATION",
                "DND start and end are required when DND is enabled.", 400,
            )
        setting, _ = NotificationSetting.objects.update_or_create(
            user=request.user,
            defaults={
                "dnd_enabled": dnd_enabled, "dnd_start": dnd_start,
                "dnd_end": dnd_end, "timezone": timezone_name,
                "updated_at": timezone.now(),
            },
        )
        categories = request.data.get("categories") or {}
        if not isinstance(categories, dict):
            raise ContractAPIException("VALIDATION_ERROR", "categories must be an object.", 400)
        for category, enabled in categories.items():
            if category not in DEFAULT_CATEGORIES:
                raise ContractAPIException("VALIDATION_ERROR", f"Unknown category: {category}", 400)
            NotificationCategoryPreference.objects.update_or_create(
                user=request.user, category=category,
                defaults={"enabled": True if category == "CRITICAL" else bool(enabled),
                          "updated_at": timezone.now()},
            )
        return Response(_preferences(request.user))
