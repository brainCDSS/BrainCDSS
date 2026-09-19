from django.urls import path

from apps.assessments.api.views import (
    AssessmentDetailView,
    AssessmentListCreateView,
    AssessmentWorklistView,
    EmergencyEventAcknowledgeView,
    EmergencyWorklistView,
    TriageReviewView,
)


urlpatterns = [
    path(
        "api/v1/assessments",
        AssessmentListCreateView.as_view(),
        name="api-asm-assessment-list-by-encounter",
    ),
    path(
        "api/v1/neurology/emergency-worklist",
        EmergencyWorklistView.as_view(),
        name="api-asm-006-real",
    ),
    path(
        "api/v1/emergency-events/<uuid:event_id>/acknowledge",
        EmergencyEventAcknowledgeView.as_view(),
        name="api-evt-001-real",
    ),
    path(
        "api/v1/assessments/worklist",
        AssessmentWorklistView.as_view(),
        name="api-asm-001-real",
    ),
    path(
        "api/v1/assessments/<uuid:assessment_id>/triage-reviews",
        TriageReviewView.as_view(),
        name="api-asm-triage-review",
    ),
    path(
        "api/v1/assessments/<uuid:assessment_id>",
        AssessmentDetailView.as_view(),
        name="api-asm-003-real",
    ),
]
