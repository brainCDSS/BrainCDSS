"""BrainOn Assistant / MCP Internal Read-only routes."""

from django.urls import path

from .chat import AssistantMessageView

from .internal_mcp import (
    AppointmentsInternalView,
    ClinicalRecordSummaryInternalView,
    CurrentMedicationsInternalView,
    EmergencyWorklistInternalView,
    ImagingAnalysisResultInternalView,
    MedicationSafetyResultInternalView,
    PatientSummaryInternalView,
    PendingConsultationsInternalView,
    RecentTestResultsInternalView,
    TodayAppointmentsInternalView,
)


urlpatterns = [
    path(
        "api/v1/assistant/messages",
        AssistantMessageView.as_view(),
        name="assistant-messages",
    ),
    path(
        "internal/v1/mcp/get_patient_summary/",
        PatientSummaryInternalView.as_view(),
        name="internal-mcp-patient-summary",
    ),
    path(
        "internal/v1/mcp/get_appointments/",
        AppointmentsInternalView.as_view(),
        name="internal-mcp-appointments",
    ),

    # MCP 응답 구조 보완 =========================
    path(
    "internal/v1/mcp/get_today_appointments/",
    TodayAppointmentsInternalView.as_view(),
    name="internal-mcp-today-appointments",
    ),

    path(
    "internal/v1/mcp/get_emergency_worklist/",
    EmergencyWorklistInternalView.as_view(),
    name="internal-mcp-emergency-worklist",
    ),

    path(
        "internal/v1/mcp/get_pending_consultations/",
        PendingConsultationsInternalView.as_view(),
        name="internal-mcp-pending-consultations",
    ),

    # =========================================

    path(
        "internal/v1/mcp/get_current_medications/",
        CurrentMedicationsInternalView.as_view(),
        name="internal-mcp-current-medications",
    ),
    path(
        "internal/v1/mcp/get_medication_safety_result/",
        MedicationSafetyResultInternalView.as_view(),
        name="internal-mcp-medication-safety",
    ),
    path(
        "internal/v1/mcp/get_recent_test_results/",
        RecentTestResultsInternalView.as_view(),
        name="internal-mcp-recent-test-results",
    ),
    path(
        "internal/v1/mcp/get_imaging_analysis_result/",
        ImagingAnalysisResultInternalView.as_view(),
        name="internal-mcp-imaging-analysis-result",
    ),
    path(
        "internal/v1/mcp/get_clinical_record_summary/",
        ClinicalRecordSummaryInternalView.as_view(),
        name="internal-mcp-clinical-record-summary",
    ),
]
