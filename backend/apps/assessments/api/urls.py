from django.urls import path

from apps.assessments.api.views import (
    AssessmentDetailView,
    AssessmentWorklistView,
    EmergencyEventAcknowledgeView,
    EmergencyWorklistView,
)


urlpatterns = [
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
        "api/v1/assessments/<uuid:assessment_id>",
        AssessmentDetailView.as_view(),
        name="api-asm-003-real",
    ),
]
