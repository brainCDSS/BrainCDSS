"""Read-only patient timeline assembled from existing clinical records."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_analysis.models import AIAnalysis, AIResultReview
from apps.assessments.models import InitialAssessment
from apps.clinical_records.models import ClinicalNote
from apps.consultations.models import Consultation
from apps.imaging.models import ImagingStudy
from apps.patients.api.permissions import role_code
from apps.patients.selectors.patients import can_view_patient
from apps.prescriptions.models import Prescription, PrescriptionItem
from apps.radiology.models import RadiologyReport


CLINICAL_READ_ROLES = {"NURSE", "NEUROLOGIST", "NEUROSURGEON", "RADIOLOGY", "MASTER"}


class PatientTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_patient_timeline",
        summary="Patient clinical timeline",
        responses={status.HTTP_200_OK: {"type": "object"}},
    )
    def get(self, request, patient_id):
        if role_code(request.user) not in CLINICAL_READ_ROLES:
            return Response({"code": "FORBIDDEN_ROLE"}, status=status.HTTP_403_FORBIDDEN)
        if not can_view_patient(request.user, patient_id):
            return Response({"code": "PATIENT_ACCESS_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        events = []

        def add(*, event_id, at, title, detail, tone):
            if at is not None:
                events.append({
                    "id": event_id,
                    "at": at,
                    "title": title,
                    "detail": detail,
                    "tone": tone,
                })

        for assessment in InitialAssessment.objects.filter(encounter__patient_id=patient_id):
            add(
                event_id=f"assessment-{assessment.id}",
                at=assessment.completed_at or assessment.updated_at or assessment.created_at,
                title="Initial assessment completed" if assessment.status == "COMPLETED" else "Initial assessment saved",
                detail="Score: " + (str(assessment.total_score) if assessment.total_score is not None else "-") + " · " + (assessment.triage_priority or assessment.status),
                tone="assessment",
            )

        for note in ClinicalNote.objects.filter(encounter__patient_id=patient_id, status="FINAL"):
            add(
                event_id=f"note-{note.id}",
                at=note.finalized_at or note.updated_at,
                title="Clinical note finalized",
                detail=(note.clinical_opinion or note.assessment or note.plan or "Clinical note recorded")[:180],
                tone="note",
            )

        for study in ImagingStudy.objects.filter(patient_id=patient_id):
            add(
                event_id=f"study-{study.id}",
                at=study.study_datetime or study.created_at,
                title="Imaging study registered",
                detail=f"{', '.join(study.modalities or [])} · {study.status}",
                tone="imaging",
            )

        for analysis in AIAnalysis.objects.filter(study__patient_id=patient_id):
            add(
                event_id=f"analysis-{analysis.id}",
                at=analysis.completed_at or analysis.requested_at,
                title="AI analysis completed" if analysis.status == "COMPLETED" else "AI analysis requested",
                detail=f"{analysis.analysis_type} · {analysis.status}",
                tone="ai",
            )

        for review in AIResultReview.objects.filter(result__analysis__study__patient_id=patient_id):
            add(
                event_id=f"ai-review-{review.id}",
                at=review.reviewed_at,
                title="AI result reviewed",
                detail=f"Decision: {review.decision}",
                tone="ai_review",
            )

        for consultation in Consultation.objects.filter(encounter__patient_id=patient_id):
            add(
                event_id=f"consultation-{consultation.id}",
                at=consultation.completed_at or consultation.accepted_at or consultation.requested_at,
                title="Consultation completed" if consultation.status in {"COMPLETED", "RESPONDED"} else "Consultation requested",
                detail=f"{consultation.consultation_type} · {consultation.status}",
                tone="consultation",
            )

        for report in RadiologyReport.objects.filter(study__patient_id=patient_id, is_current=True).exclude(status="DRAFT"):
            add(
                event_id=f"radiology-report-{report.id}",
                at=report.finalized_at or report.preliminary_at or report.updated_at,
                title="Radiology report finalized" if report.status == "FINAL" else "Radiology preliminary report",
                detail=(report.impression or report.findings or "Radiology report recorded")[:180],
                tone="radiology",
            )

        for prescription in Prescription.objects.filter(encounter__patient_id=patient_id, status="FINAL"):
            medication_names = list(
                PrescriptionItem.objects.filter(prescription_id=prescription.id)
                .order_by("created_at")
                .values_list("medication_name", flat=True)[:2]
            )
            add(
                event_id=f"prescription-{prescription.id}",
                at=prescription.finalized_at or prescription.updated_at,
                title="Prescription finalized",
                detail=", ".join(medication_names) or "Prescription recorded",
                tone="prescription",
            )

        events.sort(key=lambda event: event["at"], reverse=True)
        return Response({"count": len(events), "results": events})
