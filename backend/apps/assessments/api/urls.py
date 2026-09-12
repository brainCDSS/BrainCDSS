from django.urls import path

from apps.assessments.api.views import AssessmentDetailView, AssessmentWorklistView


urlpatterns = [
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
