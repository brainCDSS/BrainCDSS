from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import (
    AIAnalysis,
    AIAnalysisResult,
)
from apps.assessments.models import (
    AssessmentItem,
    InitialAssessment,
)
from apps.clinical_records.models import Encounter
from apps.consultations.models import Consultation
from apps.integrations.models import IntegrationTransaction
from apps.prescriptions.models import (
    Prescription,
    PrescriptionItem,
)
from apps.radiology.models import RadiologyReport


CLINICAL_CONTEXT_ROLES = {
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
    "NURSE",
}

ACTIVE_CONSULTATION_STATUSES = {
    "REQUESTED",
    "ACCEPTED",
    "IN_PROGRESS",
    "RESPONDED",
}

FINAL_REPORT_STATUSES = {
    "FINAL",
    "AMENDED",
}


class StrokePatientViewError(Exception):
    def __init__(
        self,
        code,
        detail,
        status_code,
    ):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _reference_uuid(
    value,
    field_name,
):
    text = str(value or "").strip()

    if not text:
        raise StrokePatientViewError(
            "INVALID_HOOK_REQUEST",
            f"{field_name} is required.",
            400,
        )

    if "/" in text:
        text = (
            text.rstrip("/")
            .split("/")[-1]
        )

    try:
        return uuid.UUID(text)

    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        raise StrokePatientViewError(
            "INVALID_HOOK_REQUEST",
            (
                f"{field_name} must contain "
                "a valid UUID."
            ),
            400,
        )


def _validate_hook_instance(
    value,
):
    try:
        return uuid.UUID(
            str(value)
        )

    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        raise StrokePatientViewError(
            "INVALID_HOOK_REQUEST",
            (
                "hookInstance must be "
                "a valid UUID."
            ),
            400,
        )


def _load_context(
    context,
):
    if not isinstance(
        context,
        dict,
    ):
        raise StrokePatientViewError(
            "INVALID_HOOK_REQUEST",
            "context is required.",
            400,
        )

    user_id = _reference_uuid(
        context.get("userId"),
        "context.userId",
    )

    patient_id = _reference_uuid(
        context.get("patientId"),
        "context.patientId",
    )

    encounter_id = _reference_uuid(
        context.get("encounterId"),
        "context.encounterId",
    )

    User = get_user_model()

    user = (
        User.objects
        .filter(
            id=user_id,
            is_active=True,
            role__is_active=True,
            role__code__in=(
                CLINICAL_CONTEXT_ROLES
            ),
        )
        .select_related("role")
        .first()
    )

    if user is None:
        raise StrokePatientViewError(
            "CDS_FORBIDDEN",
            (
                "Clinical user context "
                "is not permitted."
            ),
            403,
        )

    encounter = (
        Encounter.objects
        .filter(
            id=encounter_id,
            patient_id=patient_id,
        )
        .select_related("patient")
        .first()
    )

    if encounter is None:
        raise StrokePatientViewError(
            "PATIENT_CONTEXT_NOT_FOUND",
            (
                "Encounter and patient "
                "context were not found."
            ),
            404,
        )

    return (
        user,
        encounter.patient,
        encounter,
    )


def _assessment_snapshot(
    encounter,
):
    assessment = (
        InitialAssessment.objects
        .filter(
            encounter=encounter
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    if assessment is None:
        return None

    vital_items = list(
        AssessmentItem.objects
        .filter(
            assessment=assessment,
            item_group="VITAL",
        )
        .order_by(
            "recorded_at"
        )
    )

    vitals = []

    for item in vital_items:
        value = (
            str(item.value_numeric)
            if item.value_numeric
            is not None
            else item.value_text
        )

        vitals.append(
            {
                "code": item.item_code,
                "value": value,
                "unit": item.unit,
                "red_flag": (
                    item.is_red_flag
                ),
            }
        )

    return {
        "assessment_id": str(
            assessment.id
        ),
        "status": assessment.status,
        "total_score": (
            assessment.total_score
        ),
        "triage_priority": (
            assessment.triage_priority
        ),
        "onset_at": (
            assessment.onset_at
            .isoformat()
            if assessment.onset_at
            else None
        ),
        "lkw_at": (
            assessment.lkw_at
            .isoformat()
            if assessment.lkw_at
            else None
        ),
        "vitals": vitals,
    }


def _consultation_snapshot(
    encounter,
):
    rows = (
        Consultation.objects
        .filter(
            encounter=encounter,
            status__in=(
                ACTIVE_CONSULTATION_STATUSES
            ),
        )
        .order_by(
            "-requested_at"
        )
    )

    return [
        {
            "consultation_id": str(
                row.id
            ),
            "type": (
                row.consultation_type
            ),
            "priority": row.priority,
            "status": row.status,
            "reason": row.reason,
            "assigned_to_id": (
                str(row.assigned_to_id)
                if row.assigned_to_id
                else None
            ),
        }
        for row in rows
    ]


def _medication_snapshot(
    encounter,
):
    prescriptions = (
        Prescription.objects
        .filter(
            encounter=encounter,
            status="FINAL",
        )
        .values_list(
            "id",
            flat=True,
        )
    )

    rows = (
        PrescriptionItem.objects
        .filter(
            prescription_id__in=(
                prescriptions
            ),
            medication__is_active=True,
        )
        .select_related(
            "medication"
        )
        .order_by(
            "-created_at"
        )
    )

    return [
        {
            "prescription_item_id": str(
                row.id
            ),
            "medication_id": str(
                row.medication_id
            ),
            "medication_name": (
                row.medication_name
            ),
            "dose": str(row.dose),
            "dose_unit": (
                row.dose_unit
            ),
            "route": row.route,
            "frequency_per_day": (
                row.frequency_per_day
            ),
        }
        for row in rows
    ]


def _latest_ai_snapshot(
    patient,
):
    analysis = (
        AIAnalysis.objects
        .filter(
            study__patient=patient,
            status="COMPLETED",
        )
        .select_related(
            "study"
        )
        .order_by(
            "-completed_at",
            "-created_at",
        )
        .first()
    )

    if analysis is None:
        return None

    result = (
        AIAnalysisResult.objects
        .filter(
            analysis=analysis
        )
        .first()
    )

    if result is None:
        return None

    return {
        "analysis_id": str(
            analysis.id
        ),
        "study_id": str(
            analysis.study_id
        ),
        "analysis_type": (
            analysis.analysis_type
        ),
        "is_positive": (
            result.is_positive
        ),
        "confidence": (
            str(result.confidence)
            if result.confidence
            is not None
            else None
        ),
        "lesion_count": (
            result.lesion_count
        ),
        "total_volume_ml": (
            str(result.total_volume_ml)
            if result.total_volume_ml
            is not None
            else None
        ),
        "max_diameter_mm": (
            str(result.max_diameter_mm)
            if result.max_diameter_mm
            is not None
            else None
        ),
        "severity": (
            result.severity
        ),
        "generated_at": (
            result.generated_at
            .isoformat()
        ),
    }


def _latest_report_snapshot(
    patient,
):
    report = (
        RadiologyReport.objects
        .filter(
            study__patient=patient,
            status__in=(
                FINAL_REPORT_STATUSES
            ),
            is_current=True,
        )
        .select_related(
            "study"
        )
        .order_by(
            "-finalized_at",
            "-updated_at",
        )
        .first()
    )

    if report is None:
        return None

    return {
        "report_id": str(
            report.id
        ),
        "study_id": str(
            report.study_id
        ),
        "status": report.status,
        "impression": (
            report.impression
        ),
        "recommendation": (
            report.recommendation
        ),
        "critical_finding": (
            report.critical_finding
        ),
        "critical_level": (
            report.critical_level
        ),
        "finalized_at": (
            report.finalized_at
            .isoformat()
            if report.finalized_at
            else None
        ),
    }


def _build_cards(
    *,
    assessment,
    consultations,
    medications,
    ai,
    report,
):
    cards = []

    if (
        ai is not None
        and ai["is_positive"]
    ):
        detail_parts = []

        if ai[
            "total_volume_ml"
        ] is not None:
            detail_parts.append(
                (
                    "AI 분석 병변량 "
                    f"{ai['total_volume_ml']} mL"
                )
            )

        if ai[
            "confidence"
        ] is not None:
            detail_parts.append(
                (
                    "Confidence "
                    f"{ai['confidence']}"
                )
            )

        if not detail_parts:
            detail_parts.append(
                "AI 양성 소견 확인"
            )

        cards.append(
            {
                "uuid": str(
                    uuid.uuid4()
                ),
                "summary": (
                    "최근 뇌영상 AI 분석에서 "
                    "이상 소견이 확인되었습니다."
                ),
                "detail": (
                    ", ".join(
                        detail_parts
                    )
                    + ". 최종 판독을 확인하세요."
                ),
                "indicator": (
                    "critical"
                    if str(
                        ai.get(
                            "severity",
                            ""
                        )
                    ).upper()
                    in {
                        "CRITICAL",
                        "HIGH",
                        "SEVERE",
                    }
                    else "warning"
                ),
                "source": {
                    "label": (
                        "BrainOn CDSS"
                    )
                },
                "links": [
                    {
                        "label": (
                            "영상 및 AI Overlay 열기"
                        ),
                        "url": (
                            "/viewer"
                            f"?study_id="
                            f"{ai['study_id']}"
                            f"&analysis_id="
                            f"{ai['analysis_id']}"
                        ),
                        "type": "absolute",
                    }
                ],
            }
        )

    if (
        report is not None
        and report[
            "critical_finding"
        ]
    ):
        cards.append(
            {
                "uuid": str(
                    uuid.uuid4()
                ),
                "summary": (
                    "영상의학과 중요 판독 "
                    "소견이 있습니다."
                ),
                "detail": (
                    report["impression"]
                    or (
                        "중요 판독 소견을 "
                        "확인하세요."
                    )
                ),
                "indicator": "critical",
                "source": {
                    "label": (
                        "BrainOn CDSS"
                    )
                },
            }
        )

    if assessment is not None:
        red_flags = [
            item
            for item
            in assessment[
                "vitals"
            ]
            if item[
                "red_flag"
            ]
        ]

        if red_flags:
            cards.append(
                {
                    "uuid": str(
                        uuid.uuid4()
                    ),
                    "summary": (
                        "초기평가에서 Red Flag "
                        "항목이 확인되었습니다."
                    ),
                    "detail": (
                        ", ".join(
                            (
                                f"{item['code']}="
                                f"{item['value']}"
                                f"{item['unit'] or ''}"
                            )
                            for item
                            in red_flags
                        )
                    ),
                    "indicator": "warning",
                    "source": {
                        "label": (
                            "BrainOn CDSS"
                        )
                    },
                }
            )

    if consultations:
        urgent = [
            row
            for row in consultations
            if str(
                row["priority"]
            ).upper()
            in {
                "STAT",
                "URGENT",
                "HIGH",
            }
        ]

        if urgent:
            cards.append(
                {
                    "uuid": str(
                        uuid.uuid4()
                    ),
                    "summary": (
                        "긴급 협진 요청이 "
                        "진행 중입니다."
                    ),
                    "detail": (
                        f"활성 긴급 협진 "
                        f"{len(urgent)}건"
                    ),
                    "indicator": "warning",
                    "source": {
                        "label": (
                            "BrainOn CDSS"
                        )
                    },
                }
            )

    return cards


def evaluate_stroke_patient_view(
    *,
    payload,
    service_principal,
    request_id=None,
):
    if not isinstance(
        payload,
        dict,
    ):
        raise StrokePatientViewError(
            "INVALID_HOOK_REQUEST",
            (
                "CDS Hooks request "
                "must be an object."
            ),
            400,
        )

    if (
        payload.get("hook")
        != "patient-view"
    ):
        raise StrokePatientViewError(
            "INVALID_HOOK_REQUEST",
            (
                "hook must be "
                "'patient-view'."
            ),
            400,
        )

    hook_instance = (
        _validate_hook_instance(
            payload.get(
                "hookInstance"
            )
        )
    )

    (
        user,
        patient,
        encounter,
    ) = _load_context(
        payload.get(
            "context"
        )
    )

    trace_id = str(
        request_id
        or hook_instance
    )

    external_message = str(
        hook_instance
    )

    existing_transaction = (
        IntegrationTransaction.objects
        .filter(
            standard="CDS_HOOKS",
            message_type=(
                "stroke-patient-view"
            ),
            external_message=(
                external_message
            ),
        )
        .first()
    )

    assessment = (
        _assessment_snapshot(
            encounter
        )
    )

    consultations = (
        _consultation_snapshot(
            encounter
        )
    )

    medications = (
        _medication_snapshot(
            encounter
        )
    )

    ai = _latest_ai_snapshot(
        patient
    )

    report = (
        _latest_report_snapshot(
            patient
        )
    )

    cards = _build_cards(
        assessment=assessment,
        consultations=consultations,
        medications=medications,
        ai=ai,
        report=report,
    )

    if (
        existing_transaction
        is None
    ):
        now = timezone.now()

        with transaction.atomic():
            IntegrationTransaction.objects.create(
                direction="INBOUND",
                standard="CDS_HOOKS",
                source_system=(
                    service_principal
                    .service_name
                ),
                target_system=(
                    "BrainOn-CDSS"
                ),
                message_type=(
                    "stroke-patient-view"
                ),
                external_message=(
                    external_message
                ),
                trace=trace_id,
                status="SUCCESS",
                attempt_count=1,
                error_code=None,
                started_at=now,
                completed_at=(
                    timezone.now()
                ),
            )

    return {
        "cards": cards,
        "context": {
            "patient_id": str(
                patient.id
            ),
            "encounter_id": str(
                encounter.id
            ),
            "clinical_user_id": str(
                user.id
            ),
            "assessment": assessment,
            "active_consultations": (
                consultations
            ),
            "active_medications": (
                medications
            ),
            "latest_ai_result": ai,
            "current_radiology_report": (
                report
            ),
        },
        "duplicate": (
            existing_transaction
            is not None
        ),
    }
