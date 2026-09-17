from django.urls import path
from .report_views import RadiologyReportCollectionView, RadiologyReportDetailView, RadiologyReportTransitionView

urlpatterns = [
    path("api/v1/radiology-reports", RadiologyReportCollectionView.as_view()),
    path("api/v1/radiology-reports/<uuid:report_id>", RadiologyReportDetailView.as_view()),
    path("api/v1/radiology-reports/<uuid:report_id>/submit-preliminary", RadiologyReportTransitionView.as_view(), {"action": "preliminary"}),
    path("api/v1/radiology-reports/<uuid:report_id>/finalize", RadiologyReportTransitionView.as_view(), {"action": "finalize"}),
]
