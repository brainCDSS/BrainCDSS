from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_analysis.models import AIAnalysis
from apps.imaging.models import ImagingStudy
from apps.patients.selectors.patients import can_view_patient
from apps.radiology.models import RadiologyReport, RadiologyReportRevision


EDITABLE_STATES = {"DRAFT", "PRELIMINARY"}


def _require_radiology(user):
    if getattr(getattr(user, "role", None), "code", None) not in {
        "RADIOLOGY",
        "MASTER",
    }:
        raise PermissionDenied("RADIOLOGY or MASTER role is required.")


def _study_for_actor(study_id, actor):
    study = ImagingStudy.objects.select_related("patient").filter(pk=study_id).first()
    if study is None:
        raise NotFound("Imaging study was not found.")
    if study.patient_id is None or not can_view_patient(actor, study.patient_id):
        raise PermissionDenied("You do not have access to this study.")
    return study


def _report_for_actor(report_id, actor, *, editable=False):
    report = RadiologyReport.objects.select_related("study__patient").filter(pk=report_id, is_current=True).first()
    if report is None:
        raise NotFound("Radiology report was not found.")
    if report.study.patient_id is None or not can_view_patient(actor, report.study.patient_id):
        raise PermissionDenied("You do not have access to this report.")
    if editable and report.status not in EDITABLE_STATES:
        raise ValidationError({"code": "REPORT_IMMUTABLE", "detail": "This report is no longer editable."})
    return report


def _serialize(report):
    return {
        "report_id": str(report.id), "study_id": str(report.study_id), "status": report.status,
        "version": report.version, "findings": report.findings, "impression": report.impression,
        "recommendation": report.recommendation, "structured_findings": report.structured_findings,
        "author": {"user_id": str(report.author_id)},
        "finalized_by": {"user_id": str(report.finalized_by_id)} if report.finalized_by_id else None,
        "finalized_at": report.finalized_at, "critical_finding": report.critical_finding,
        "critical_level": report.critical_level,
    }


def _snapshot(report):
    return {
        "status": report.status, "version": report.version, "findings": report.findings,
        "impression": report.impression, "recommendation": report.recommendation,
        "structured_findings": report.structured_findings, "critical_finding": report.critical_finding,
        "critical_level": report.critical_level,
    }


def _revision(report, actor, previous, reason):
    RadiologyReportRevision.objects.create(
        report=report, version=report.version, previous_snapshot=previous,
        new_snapshot=_snapshot(report), change_reason=reason, changed_by=actor,
        changed_at=timezone.now(),
    )


def _payload(data, *, require_content=False):
    if not isinstance(data, dict):
        raise ValidationError("JSON object is required.")
    findings = str(data.get("findings") or "").strip()
    impression = str(data.get("impression") or "").strip()
    if require_content and (not findings or not impression):
        raise ValidationError({"code": "REPORT_CONTENT_REQUIRED", "detail": "Findings and impression are required."})
    critical = bool(data.get("critical_finding", False))
    level = str(data.get("critical_level") or "NONE")
    if level not in {"NONE", "URGENT", "CRITICAL"} or (critical and level == "NONE") or (not critical and level != "NONE"):
        raise ValidationError({"code": "INVALID_CRITICAL_LEVEL", "detail": "Critical finding and level are inconsistent."})
    structured = data.get("structured_findings", {})
    if not isinstance(structured, dict):
        raise ValidationError({"structured_findings": "Object is required."})
    return findings, impression, str(data.get("recommendation") or "").strip(), structured, critical, level


class RadiologyReportCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        _require_radiology(request.user)
        study_id = request.data.get("study_id") if isinstance(request.data, dict) else None
        if not study_id:
            raise ValidationError({"study_id": "This field is required."})
        study = _study_for_actor(study_id, request.user)
        if study.status != "AVAILABLE":
            raise ValidationError({"code": "STUDY_NOT_AVAILABLE", "detail": "Study must be AVAILABLE."})
        if RadiologyReport.objects.select_for_update().filter(study=study, is_current=True, status__in=EDITABLE_STATES).exists():
            raise ValidationError({"code": "REPORT_DRAFT_ALREADY_EXISTS", "detail": "An editable report already exists."})
        ai_id = request.data.get("referenced_ai_analysis_id")
        analysis = None
        if ai_id:
            analysis = AIAnalysis.objects.filter(pk=ai_id, study=study, status="COMPLETED").first()
            if analysis is None:
                raise ValidationError({"referenced_ai_analysis_id": "Completed analysis for this study is required."})
        findings, impression, recommendation, structured, critical, level = _payload(request.data)
        now = timezone.now()
        report = RadiologyReport.objects.create(study=study, referenced_ai_analysis=analysis, status="DRAFT", version=1, is_current=True, findings=findings, impression=impression, recommendation=recommendation, structured_findings=structured, author=request.user, critical_finding=critical, critical_level=level, created_at=now, updated_at=now)
        _revision(report, request.user, {}, "DRAFT_CREATED")
        return Response(_serialize(report), status=status.HTTP_201_CREATED)


class RadiologyReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, report_id):
        return Response(_serialize(_report_for_actor(report_id, request.user)))

    @transaction.atomic
    def patch(self, request, report_id):
        _require_radiology(request.user)
        report = _report_for_actor(report_id, request.user, editable=True)
        if request.data.get("version") != report.version:
            raise ValidationError({"code": "REPORT_VERSION_CONFLICT", "detail": "Refresh the report and try again."})
        previous = _snapshot(report)
        findings, impression, recommendation, structured, critical, level = _payload(request.data)
        report.findings, report.impression, report.recommendation = findings, impression, recommendation
        report.structured_findings, report.critical_finding, report.critical_level = structured, critical, level
        report.version += 1; report.updated_at = timezone.now(); report.save()
        _revision(report, request.user, previous, "DRAFT_UPDATED")
        return Response(_serialize(report))


class RadiologyReportTransitionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, report_id, action):
        _require_radiology(request.user)
        report = _report_for_actor(report_id, request.user, editable=True)
        if request.data.get("version") != report.version:
            raise ValidationError({"code": "REPORT_VERSION_CONFLICT", "detail": "Refresh the report and try again."})
        if request.data.get("confirmation") is not True:
            raise ValidationError({"confirmation": "Confirmation is required."})
        if not report.findings or not report.impression:
            raise ValidationError({"code": "REPORT_CONTENT_REQUIRED", "detail": "Findings and impression are required."})
        if action == "preliminary":
            if report.status != "DRAFT": raise ValidationError({"code": "PRELIMINARY_INVALID_STATE"})
            next_status = "PRELIMINARY"; reason = "PRELIMINARY_SUBMITTED"; report.preliminary_at = timezone.now()
        elif action == "finalize":
            next_status = "FINAL"; reason = "FINALIZED"; report.finalized_by = request.user; report.finalized_at = timezone.now()
        else: raise NotFound()
        previous = _snapshot(report); report.status = next_status; report.version += 1; report.updated_at = timezone.now(); report.save()
        _revision(report, request.user, previous, reason)
        return Response(_serialize(report))
