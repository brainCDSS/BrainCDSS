"""BrainOn MCP 전용 Read-only Django Internal API."""

from datetime import timedelta
from uuid import UUID

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_analysis.models import AIAnalysisResult
from apps.appointments.models import Appointment
from apps.assessments.models import (EmergencyEvent, InitialAssessment,)
from apps.clinical_records.models import ClinicalNote, Encounter
from apps.medication_safety.services.medication_safety import (
    MedicationSafetyError,
    check_medication_safety,
)
from apps.patients.models import Patient
from apps.prescriptions.models import PrescriptionItem
from apps.consultations.models import Consultation
from .permissions import MCPBackendTokenPermission


# ============================================================
# 공통 처리
# ============================================================

class MCPReadOnlyView(APIView):
    """MCP Service Token으로만 접근 가능한 Read-only Internal API."""

    authentication_classes = []
    permission_classes = [MCPBackendTokenPermission]

    def get_patient(self, request):
        raw_patient_id = (
            request.query_params.get("patient_id", "").strip()
        )

        try:
            patient_id = UUID(raw_patient_id)
        except (TypeError, ValueError, AttributeError):
            return None, Response(
                {
                    "status": "ERROR",
                    "code": "INVALID_PATIENT_ID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient = (
            Patient.objects
            .filter(id=patient_id)
            .first()
        )

        if patient is None:
            return None, Response(
                {
                    "status": "ERROR",
                    "code": "PATIENT_NOT_FOUND",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return patient, None

    @staticmethod
    def ok(data):
        return Response(
            {
                "status": "OK",
                "is_mock": False,
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# 1. 환자 기본 요약
# ============================================================

class PatientSummaryInternalView(MCPReadOnlyView):
    """환자의 MCP 기본 요약."""

    @extend_schema(exclude=True)
    def get(self, request):
        patient, error = self.get_patient(request)

        if error:
            return error

        return self.ok(
            {
                "id": str(patient.id),
                "patient_no": patient.patient_no,
                "name": patient.name,
                "birth_date": patient.birth_date,
                "estimated_age": patient.estimated_age,
                "sex": patient.sex,
                "status": patient.status,
                "pregnancy_status": (
                    patient.pregnancy_status
                ),
                "allergy_info": patient.allergy_info,
            }
        )


# ============================================================
# 2. 예약 조회
# ============================================================

class AppointmentsInternalView(MCPReadOnlyView):
    """환자의 최근 예약 정보."""

    @extend_schema(exclude=True)
    def get(self, request):
        patient, error = self.get_patient(request)

        if error:
            return error

        appointments = (
            Appointment.objects
            .filter(patient=patient)
            .select_related(
                "hospital",
                "department",
                "clinician__user",
                "slot",
            )
            .order_by("-requested_at")[:20]
        )

        items = []

        for appointment in appointments:
            items.append(
                {
                    "id": str(appointment.id),
                    "status": appointment.status,
                    "request_type": (
                        appointment.request_type
                    ),
                    "hospital": (
                        appointment.hospital.name
                    ),
                    "department": (
                        appointment.department.name
                    ),
                    "clinician": (
                        appointment.clinician.user.name
                    ),
                    "specialty": (
                        appointment.clinician.specialty
                    ),
                    "start_at": (
                        appointment.slot.start_at
                    ),
                    "end_at": appointment.slot.end_at,
                    "requested_at": (
                        appointment.requested_at
                    ),
                    "confirmed_at": (
                        appointment.confirmed_at
                    ),
                    "cancelled_at": (
                        appointment.cancelled_at
                    ),
                    "completed_at": (
                        appointment.completed_at
                    ),
                }
            )

        return self.ok(
            {
                "count": len(items),
                "items": items,
            }
        )

# ============================================================
# 2-1. 오늘 전체 예약 현황: MCP 응답 기능 보완
# ============================================================

class TodayAppointmentsInternalView(MCPReadOnlyView):
    """오늘 예약된 전체 환자 현황을 조회한다."""

    @extend_schema(exclude=True)
    def get(self, request):
        today = timezone.localdate()

        appointments = (
            Appointment.objects
            .filter(
                slot__start_at__date=today,
            )
            .select_related(
                "patient",
                "hospital",
                "department",
                "clinician__user",
                "slot",
            )
            .order_by(
                "slot__start_at",
            )[:200]
        )

        items = []
        status_counts = {}

        for appointment in appointments:
            status_code = str(
                appointment.status or ""
            )

            status_counts[status_code] = (
                status_counts.get(
                    status_code,
                    0,
                )
                + 1
            )

            items.append(
                {
                    "id": str(
                        appointment.id
                    ),
                    "patient_id": str(
                        appointment.patient_id
                    ),
                    "patient_no": (
                        appointment.patient.patient_no
                    ),
                    "patient_name": (
                        appointment.patient.name
                    ),
                    "status": (
                        appointment.status
                    ),
                    "request_type": (
                        appointment.request_type
                    ),
                    "hospital": (
                        appointment.hospital.name
                    ),
                    "department": (
                        appointment.department.name
                    ),
                    "clinician": (
                        appointment.clinician.user.name
                    ),
                    "specialty": (
                        appointment.clinician.specialty
                    ),
                    "start_at": (
                        appointment.slot.start_at
                    ),
                    "end_at": (
                        appointment.slot.end_at
                    ),
                }
            )

        return self.ok(
            {
                "date": today,
                "count": len(items),
                "status_counts": (
                    status_counts
                ),
                "items": items,
            }
        )

# ============================================================
# Global 2. 현재 응급환자 Worklist
# ============================================================

class EmergencyWorklistInternalView(
    MCPReadOnlyView
):
    """
    현재 종료되지 않은 Encounter에 연결된
    EmergencyEvent를 조회한다.

    MCP Server가 DB를 직접 조회하지 않고
    이 Django Internal API를 통해서만 조회한다.

    EmergencyEvent.status의 종료 상태값을
    임의로 새로 정의하지 않는다.

    현재 진행 중인 임상 흐름이라는 명확한 기준으로
    Encounter.ended_at이 없는 건만 조회한다.
    """

    @extend_schema(exclude=True)
    def get(self, request):
        events = (
            EmergencyEvent.objects
            .filter(
                encounter__ended_at__isnull=True,
            )
            .select_related(
                "assessment",
                "encounter",
                "encounter__patient",
                "assigned_neurologist",
                "acknowledged_by",
            )
            .order_by(
                "-occurred_at",
            )[:200]
        )

        items = []
        status_counts = {}
        patient_ids = set()

        for event in events:
            patient = (
                event.encounter.patient
            )

            status_code = str(
                event.status or ""
            )

            status_counts[status_code] = (
                status_counts.get(
                    status_code,
                    0,
                )
                + 1
            )

            patient_ids.add(
                str(patient.id)
            )

            items.append(
                {
                    "event_id": str(
                        event.id
                    ),
                    "patient_id": str(
                        patient.id
                    ),
                    "patient_no": (
                        patient.patient_no
                    ),
                    "patient_name": (
                        patient.name
                    ),
                    "encounter_id": str(
                        event.encounter_id
                    ),
                    "encounter_no": (
                        event.encounter.encounter_no
                    ),
                    "encounter_status": (
                        event.encounter.status
                    ),
                    "event_type": (
                        event.event_type
                    ),
                    "priority": (
                        event.priority
                    ),
                    "status": (
                        event.status
                    ),
                    "assigned_neurologist": (
                        event
                        .assigned_neurologist
                        .name
                    ),
                    "occurred_at": (
                        event.occurred_at
                    ),
                    "acknowledged": (
                        event.acknowledged_at
                        is not None
                    ),
                    "acknowledged_at": (
                        event.acknowledged_at
                    ),
                }
            )

        return self.ok(
            {
                "event_count": len(items),
                "patient_count": (
                    len(patient_ids)
                ),
                "status_counts": (
                    status_counts
                ),
                "items": items,
            }
        )

# ============================================================
# Global 3. 처리 대기 중 협진 Worklist
# ============================================================

class PendingConsultationsInternalView(
    MCPReadOnlyView
):
    """
    아직 회신 완료 전 단계에 있는 협진을 조회한다.

    BrainOn 협진 상태 정책 중:

    REQUESTED
    ACCEPTED
    IN_PROGRESS

    세 상태를 처리 대기/진행 중인 협진으로 본다.

    RESPONDED는 이미 회신이 생성된 상태이므로
    pending worklist에서는 제외한다.
    """

    PENDING_STATUSES = (
        "REQUESTED",
        "ACCEPTED",
        "IN_PROGRESS",
    )

    @extend_schema(exclude=True)
    def get(self, request):
        consultations = (
            Consultation.objects
            .filter(
                status__in=(
                    self.PENDING_STATUSES
                )
            )
            .select_related(
                "encounter",
                "encounter__patient",
                "requested_by",
                "assigned_to",
            )
            .order_by(
                "requested_at",
            )[:200]
        )

        items = []
        status_counts = {}

        for consultation in consultations:
            patient = (
                consultation
                .encounter
                .patient
            )

            status_code = str(
                consultation.status
                or ""
            )

            status_counts[status_code] = (
                status_counts.get(
                    status_code,
                    0,
                )
                + 1
            )

            items.append(
                {
                    "consultation_id": str(
                        consultation.id
                    ),
                    "patient_id": str(
                        patient.id
                    ),
                    "patient_no": (
                        patient.patient_no
                    ),
                    "patient_name": (
                        patient.name
                    ),
                    "encounter_id": str(
                        consultation.encounter_id
                    ),
                    "encounter_no": (
                        consultation
                        .encounter
                        .encounter_no
                    ),
                    "consultation_type": (
                        consultation
                        .consultation_type
                    ),
                    "priority": (
                        consultation.priority
                    ),
                    "status": (
                        consultation.status
                    ),
                    "requested_by": (
                        consultation
                        .requested_by
                        .name
                    ),
                    "assigned_to": (
                        consultation
                        .assigned_to
                        .name
                        if consultation.assigned_to
                        else None
                    ),
                    "requested_at": (
                        consultation.requested_at
                    ),
                    "accepted_at": (
                        consultation.accepted_at
                    ),
                    "started_at": (
                        consultation.started_at
                    ),
                }
            )

        return self.ok(
            {
                "count": len(items),
                "pending_statuses": list(
                    self.PENDING_STATUSES
                ),
                "status_counts": (
                    status_counts
                ),
                "items": items,
            }
        )

# ============================================================
# Current Medication 공통 조회
# ============================================================

def _current_prescription_items(patient):
    """
    처방 시작일과 기간을 기준으로 현재 투약기간에 해당하는 약물을 조회한다.

    Prescription.status 값 자체는 별도 Contract이므로
    임의의 ACTIVE/FINALIZED 상태값을 가정하지 않는다.
    명시적인 취소/중단 상태만 제외한다.
    """

    today = timezone.localdate()

    queryset = (
        PrescriptionItem.objects
        .filter(
            prescription__encounter__patient=patient,
            prescription__status="FINAL",
            medication__is_active=True,
            start_date__lte=today,
        )
        .select_related(
            "prescription",
            "medication",
        )
        .order_by("-start_date")[:200]
    )

    inactive_statuses = {
        "CANCELLED",
        "CANCELED",
        "VOIDED",
        "DISCONTINUED",
    }

    current = []

    for item in queryset:
        prescription_status = str(
            item.prescription.status or ""
        ).upper()

        if prescription_status in inactive_statuses:
            continue

        duration_days = int(item.duration_days)

        if duration_days <= 0:
            continue

        end_date = (
            item.start_date
            + timedelta(days=duration_days - 1)
        )

        if end_date < today:
            continue

        current.append(
            {
                "object": item,
                "end_date": end_date,
            }
        )

    return current


# ============================================================
# 3. 현재 약물 조회
# ============================================================

class CurrentMedicationsInternalView(MCPReadOnlyView):
    """현재 투약기간에 해당하는 처방 약물 조회."""

    @extend_schema(exclude=True)
    def get(self, request):
        patient, error = self.get_patient(request)

        if error:
            return error

        current = _current_prescription_items(
            patient
        )

        items = []

        for row in current:
            item = row["object"]
            medication = item.medication

            items.append(
                {
                    "prescription_id": str(
                        item.prescription_id
                    ),
                    "prescription_item_id": str(
                        item.id
                    ),
                    "prescription_status": (
                        item.prescription.status
                    ),
                    "medication_id": str(
                        item.medication_id
                    ),
                    "medication_code": (
                        item.medication_code
                        or medication.medication_code
                    ),
                    "medication_name": (
                        item.medication_name
                    ),
                    "dosage_form": (
                        medication.dosage_form
                    ),
                    "strength": medication.strength,
                    "dose": item.dose,
                    "dose_unit": item.dose_unit,
                    "route": item.route,
                    "frequency_per_day": (
                        item.frequency_per_day
                    ),
                    "timing": item.timing,
                    "start_date": item.start_date,
                    "end_date": row["end_date"],
                    "duration_days": (
                        item.duration_days
                    ),
                    "instructions": (
                        item.instructions
                    ),
                }
            )

        return self.ok(
            {
                "as_of": timezone.now(),
                "count": len(items),
                "items": items,
            }
        )


# ============================================================
# 4. Medication Safety 결과
# ============================================================

class MedicationSafetyResultInternalView(
    MCPReadOnlyView
):
    """
    현재 처방 약물을 기준으로 로컬 DUR DB Medication Safety를 실시간 평가한다.

    별도의 Safety Result 저장 테이블을 임의 생성하지 않는다.
    기존 MedicationSafetyService를 그대로 사용한다.
    """

    @extend_schema(exclude=True)
    def get(self, request):
        patient, error = self.get_patient(request)

        if error:
            return error

        current = _current_prescription_items(
            patient
        )

        if not current:
            return self.ok(
                {
                    "evaluated": False,
                    "source": (
                        "LIVE_LOCAL_DUR_EVALUATION"
                    ),
                    "reason": (
                        "NO_CURRENT_MEDICATIONS"
                    ),
                    "safe": None,
                    "alerts": [],
                }
            )

        medications = []

        for row in current:
            item = row["object"]

            medications.append(
                {
                    "medication_id": str(
                        item.medication_id
                    ),
                    "dose": item.dose,
                    "unit": item.dose_unit,
                    "frequency_per_day": (
                        item.frequency_per_day
                    ),
                    "duration_days": (
                        item.duration_days
                    ),
                    "route": item.route,
                }
            )

        try:
            result = check_medication_safety(
                medications=medications,
                patient=patient,
            )

        except MedicationSafetyError as exc:
            return self.ok(
                {
                    "evaluated": False,
                    "source": (
                        "LIVE_LOCAL_DUR_EVALUATION"
                    ),
                    "code": exc.code,
                    "detail": exc.detail,
                    "medication_count": (
                        len(medications)
                    ),
                }
            )

        result["evaluated"] = True
        result["source"] = (
            "LIVE_LOCAL_DUR_EVALUATION"
        )
        result["medication_count"] = (
            len(medications)
        )

        return self.ok(result)


# ============================================================
# 5. 최근 검사 결과
# ============================================================

class RecentTestResultsInternalView(
    MCPReadOnlyView
):
    """
    test_results domain은 현재 승인된 DB Model이 없는 상태다.

    다른 임상 데이터를 검사결과로 위장하지 않고
    명시적으로 unavailable 상태를 반환한다.
    """

    @extend_schema(exclude=True)
    def get(self, request):
        patient, error = self.get_patient(request)

        if error:
            return error

        return self.ok(
            {
                "patient_id": str(patient.id),
                "available": False,
                "code": (
                    "TEST_RESULTS_DOMAIN_NOT_IMPLEMENTED"
                ),
                "count": 0,
                "items": [],
            }
        )


# ============================================================
# 6. 영상 AI 분석 결과
# ============================================================

class ImagingAnalysisResultInternalView(
    MCPReadOnlyView
):
    """환자의 최근 실제 AI Analysis Result 조회."""

    @extend_schema(exclude=True)
    def get(self, request):
        patient, error = self.get_patient(request)

        if error:
            return error

        results = (
            AIAnalysisResult.objects
            .filter(
                analysis__study__patient=patient
            )
            .select_related(
                "analysis",
                "analysis__study",
                "analysis__model_version",
                "analysis__model_version__model",
            )
            .order_by("-generated_at")[:10]
        )

        items = []

        for result in results:
            analysis = result.analysis
            study = analysis.study
            model_version = (
                analysis.model_version
            )

            items.append(
                {
                    "result_id": str(result.id),
                    "analysis_id": str(
                        analysis.id
                    ),
                    "analysis_type": (
                        analysis.analysis_type
                    ),
                    "analysis_status": (
                        analysis.status
                    ),
                    "analysis_stage": (
                        analysis.stage
                    ),
                    "model": (
                        model_version.model.display_name
                    ),
                    "model_version": (
                        model_version.version
                    ),
                    "study_id": str(study.id),
                    "study_description": (
                        study.study_description
                    ),
                    "modalities": study.modalities,
                    "study_datetime": (
                        study.study_datetime
                    ),
                    "is_positive": (
                        result.is_positive
                    ),
                    "confidence": (
                        result.confidence
                    ),
                    "lesion_count": (
                        result.lesion_count
                    ),
                    "total_volume_ml": (
                        result.total_volume_ml
                    ),
                    "max_diameter_mm": (
                        result.max_diameter_mm
                    ),
                    "severity": result.severity,
                    "structured_findings": (
                        result.structured_findings
                    ),
                    "generated_at": (
                        result.generated_at
                    ),
                }
            )

        return self.ok(
            {
                "count": len(items),
                "items": items,
            }
        )


# ============================================================
# 7. 임상기록 요약
# ============================================================

class ClinicalRecordSummaryInternalView(
    MCPReadOnlyView
):
    """
    Encounter + ClinicalNote + InitialAssessment 기반
    Read-only 임상기록 요약.
    """

    @extend_schema(exclude=True)
    def get(self, request):
        patient, error = self.get_patient(request)

        if error:
            return error

        encounters = (
            Encounter.objects
            .filter(patient=patient)
            .order_by("-arrived_at")[:10]
        )

        notes = (
            ClinicalNote.objects
            .filter(
                encounter__patient=patient
            )
            .select_related(
                "encounter",
                "author",
            )
            .order_by("-created_at")[:10]
        )

        assessments = (
            InitialAssessment.objects
            .filter(
                encounter__patient=patient
            )
            .select_related(
                "encounter",
                "assessor",
                "assigned_neurologist",
            )
            .order_by("-created_at")[:5]
        )

        encounter_items = [
            {
                "id": str(item.id),
                "encounter_no": (
                    item.encounter_no
                ),
                "encounter_type": (
                    item.encounter_type
                ),
                "status": item.status,
                "arrived_at": item.arrived_at,
                "started_at": item.started_at,
                "ended_at": item.ended_at,
            }
            for item in encounters
        ]

        note_items = [
            {
                "id": str(item.id),
                "encounter_id": str(
                    item.encounter_id
                ),
                "author": item.author.name,
                "status": item.status,
                "subjective": item.subjective,
                "objective": item.objective,
                "assessment": item.assessment,
                "plan": item.plan,
                "clinical_opinion": (
                    item.clinical_opinion
                ),
                "finalized_at": (
                    item.finalized_at
                ),
                "created_at": item.created_at,
            }
            for item in notes
        ]

        assessment_items = []

        for item in assessments:
            assigned = (
                item.assigned_neurologist.name
                if item.assigned_neurologist
                else None
            )

            assessment_items.append(
                {
                    "id": str(item.id),
                    "encounter_id": str(
                        item.encounter_id
                    ),
                    "assessor": (
                        item.assessor.name
                    ),
                    "assigned_neurologist": (
                        assigned
                    ),
                    "status": item.status,
                    "total_score": (
                        item.total_score
                    ),
                    "triage_priority": (
                        item.triage_priority
                    ),
                    "onset_at": item.onset_at,
                    "lkw_at": item.lkw_at,
                    "symptom_note": (
                        item.symptom_note
                    ),
                    "completed_at": (
                        item.completed_at
                    ),
                }
            )

        return self.ok(
            {
                "patient_id": str(patient.id),
                "encounters": encounter_items,
                "clinical_notes": note_items,
                "initial_assessments": (
                    assessment_items
                ),
            }
        )
