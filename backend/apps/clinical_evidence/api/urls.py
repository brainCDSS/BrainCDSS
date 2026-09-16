from django.urls import path

from .views import ClinicalEvidenceView

urlpatterns = [path("clinical-evidence", ClinicalEvidenceView.as_view(), name="clinical-evidence")]
