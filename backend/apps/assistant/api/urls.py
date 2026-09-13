"""BrainOn Assistant / MCP Internal Read-only routes."""

from django.urls import path

from .chat import AssistantMessageView

from .internal_mcp import (
    AppointmentsInternalView,
    ClinicalRecordSummaryInternalView,
    CurrentMedicationsInternalView,
    ImagingAnalysisResultInternalView,
    MedicationSafetyResultInternalView,
    PatientSummaryInternalView,
    RecentTestResultsInternalView,
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
