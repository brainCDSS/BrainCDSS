from django.urls import path

from apps.imaging.api.imaging_study_views import (
    ImagingStudyDetailView,
    ImagingSeriesDetailView,
    ImagingStudyAIHistoryView,
    ImagingStudyKeyImagesView,
    ImagingStudyListView,
    ImagingStudySeriesView,
)


from apps.imaging.api.viewer_views import (
    ImagingViewerContextView,
    ImagingViewerSessionView,
)

from apps.imaging.api.imaging_order_views import (
    ImagingOrderCancelView,
    ImagingOrderDetailUpdateView,
    ImagingOrderListCreateView,
)

from apps.imaging.api.imaging_history_views import (
    ImagingOrderTimelineView,
    ImagingStudyReportsView,
)
from apps.imaging.api.patient_test_results_views import PatientTestResultsView

from apps.imaging.api.imaging_remaining_views import (
    DicomArtifactStowView,
    DicomQidoSeriesView,
    DicomTransferRetryView,
    ImagingOrderStatusEventView,
    ImagingReconciliationListView,
    ImagingReconciliationResolveView,
    ImagingStudyResyncView,
    OrthancStableStudyView,
)

urlpatterns = [
    path(
        "api/v1/me/test-results",
        PatientTestResultsView.as_view(),
        name="patient_test_results",
    ),
    path(
        "api/v1/imaging-studies/<uuid:study_id>/resync",
        ImagingStudyResyncView.as_view(),
        name="api_img_008_real",
    ),
    path(
        "internal/v1/orthanc/events/stable-study",
        OrthancStableStudyView.as_view(),
        name="api_img_011_real",
    ),
    path(
        "internal/v1/imaging-orders/<uuid:order_id>/status-events",
        ImagingOrderStatusEventView.as_view(),
        name="api_img_016_real",
    ),
    path(
        "api/v1/imaging-reconciliation-tasks",
        ImagingReconciliationListView.as_view(),
        name="api_img_017_real",
    ),
    path(
        "api/v1/imaging-reconciliation-tasks/<uuid:task_id>/resolve",
        ImagingReconciliationResolveView.as_view(),
        name="api_img_018_real",
    ),
    path(
        "api/v1/dicom-transfer-jobs/<uuid:job_id>/retry",
        DicomTransferRetryView.as_view(),
        name="api_img_019_real",
    ),
    path(
        "dicom-web/studies/<str:study_instance_uid>/series",
        DicomQidoSeriesView.as_view(),
        name="api_dicom_001_real",
    ),
    path(
        "internal/v1/dicom/artifacts/stow",
        DicomArtifactStowView.as_view(),
        name="api_dicom_003_real",
    ),

    path(
        "api/v1/imaging-studies/<uuid:study_id>/reports",
        ImagingStudyReportsView.as_view(),
        name="api_img_010_real",
    ),
    path(
        "api/v1/imaging-orders/<uuid:order_id>/timeline",
        ImagingOrderTimelineView.as_view(),
        name="api_img_015_real",
    ),

    path(
        "api/v1/imaging-orders",
        ImagingOrderListCreateView.as_view(),
        name="api_img_001_012_real",
    ),
    path(
        "api/v1/imaging-orders/<uuid:order_id>/cancel",
        ImagingOrderCancelView.as_view(),
        name="api_img_014_real",
    ),
    path(
        "api/v1/imaging-orders/<uuid:order_id>",
        ImagingOrderDetailUpdateView.as_view(),
        name="api_img_002_013_real",
    ),

    path(
        "api/v1/imaging-studies/<uuid:study_id>/viewer-context",
        ImagingViewerContextView.as_view(),
        name="api_dicom_002_real",
    ),
    path(
        "api/v1/imaging-studies/<uuid:study_id>/viewer-session",
        ImagingViewerSessionView.as_view(),
        name="api_img_007_real",
    ),

    path(
        "api/v1/imaging-series/<uuid:series_id>",
        ImagingSeriesDetailView.as_view(),
        name="api_img_006_real",
    ),
    path(
        "api/v1/imaging-studies/<uuid:study_id>/key-images",
        ImagingStudyKeyImagesView.as_view(),
        name="api_img_020_021_real",
    ),
    path(
        "api/v1/imaging-studies",
        ImagingStudyListView.as_view(),
        name="api_img_003_real",
    ),
    path(
        "api/v1/imaging-studies/<uuid:study_id>/ai-analyses",
        ImagingStudyAIHistoryView.as_view(),
        name="api_img_009_real",
    ),
    path(
        "api/v1/imaging-studies/<uuid:study_id>/series",
        ImagingStudySeriesView.as_view(),
        name="api_img_005_real",
    ),
    path(
        "api/v1/imaging-studies/<uuid:study_id>",
        ImagingStudyDetailView.as_view(),
        name="api_img_004_real",
    ),
]
