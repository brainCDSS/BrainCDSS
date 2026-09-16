"""BrainOn Backend 최상위 URL 라우팅."""

from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.common.views import health
from apps.ai_analysis.api.development import DevelopmentAnalysisView
from apps.ai_analysis.api.inference import (
    AnalysisCollectionView,
    AnalysisDetailView,
    AnalysisResultView,
    AIResultReviewCollectionView,
    AnalysisNiftiViewerView,
    ResultArtifactContentView,
)
from apps.imaging.api.nifti import NiftiArtifactContentView, StudyAIInputsView


# ============================================================
# 1. 기본 API / 공통 엔드포인트
# ============================================================

urlpatterns = [
    path("api/v1/", include("apps.clinical_evidence.api.urls")),
    # Real AI analysis and NIfTI routes must precede generated fallbacks.
    path("api/v1/ai-analyses", AnalysisCollectionView.as_view()),
    path("api/v1/ai-analyses/<uuid:analysis_id>", AnalysisDetailView.as_view()),
    path(
        "api/v1/ai-analyses/<uuid:analysis_id>/result",
        AnalysisResultView.as_view(),
    ),
    path(
        "api/v1/ai-analyses/<uuid:analysis_id>/nifti-viewer",
        AnalysisNiftiViewerView.as_view(),
    ),
    path(
        "api/v1/ai-result-artifacts/<uuid:artifact_id>/content",
        ResultArtifactContentView.as_view(),
    ),
    path(
        "api/v1/ai-results/<uuid:result_id>/reviews",
        AIResultReviewCollectionView.as_view(),
    ),
    path(
        "api/v1/imaging-studies/<uuid:study_id>/ai-inputs",
        StudyAIInputsView.as_view(),
    ),
    path(
        "api/v1/nifti-artifacts/<uuid:artifact_id>/content",
        NiftiArtifactContentView.as_view(),
    ),
    path("api/v1/dev/ai-analyses", DevelopmentAnalysisView.as_view()),
    path(
        "api/v1/dev/ai-analyses/<uuid:analysis_id>",
        DevelopmentAnalysisView.as_view(),
    ),
    # 조직
    path(
        "api/v1/",
        include("apps.organizations.api.urls"),
    ),

    # 환자
    path(
        "api/v1/",
        include("apps.patients.api.urls"),
    ),

    # 서버 상태 확인
    path(
        "api/v1/health/",
        health,
        name="health",
    ),

    # OpenAPI Schema
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="openapi-schema",
    ),

    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="openapi-schema"
        ),
        name="swagger-ui",
    ),
]


# ============================================================
# 2. 실제 구현 완료 API
#
# 중요:
# 실제 구현 API는 generated fallback보다 반드시 먼저 등록한다.
# 같은 URL이 존재하더라도 Django는 먼저 등록된 URL을 사용한다.
# ============================================================

urlpatterns += [
    # 인증 / 사용자 / 권한
    path(
        "",
        include("apps.accounts.api.urls"),
    ),

    # Audit / 공통 Backend API
    path(
        "",
        include("apps.audit.api.urls"),
    ),
    path(
        "",
        include("apps.common.api.urls"),
    ),

    # Assistant / internal MCP read-only API
    path(
        "",
        include("apps.assistant.api.urls"),
    ),

    # DUR / Medication Safety
    path(
        "",
        include(
            "apps.medication_safety.api.urls"
        ),
    ),

    # Notification / FCM
    # 실제 FCM API를 generated fallback보다 먼저 등록한다.
    path(
        "",
        include(
            "apps.notifications.api.urls"
        ),
    ),

    # 처방 / RX Safety
    path(
        "",
        include(
            "apps.prescriptions.api.urls"
        ),
    ),

    # Encounter 등록 (예약 외래 / Walk-in / 응급)
    path(
        "",
        include("apps.clinical_records.api.urls"),
    ),

    # 초기평가 Worklist
    path(
        "",
        include("apps.assessments.api.urls"),
    ),

    # Appointment extensions registered before generated fallback routes.
    path(
        "",
        include("apps.appointments.api.urls"),
    ),

    # CDS Hooks
    # API-CDS-001 ~ API-CDS-004
    path(
        "",
        include("apps.cdss.api.urls"),
    ),

    # Surgical Planning Extension
    # 기존 DB66/API 기준 외 프로젝트 확장 기능
    path(
        "",
        include(
            "apps.surgical_planning.api.urls"
        ),
    ),

    # Imaging / DICOM / Viewer / Imaging Order
    # 실제 구현된 Imaging API를 generated API보다 우선 사용
    path(
        "",
        include("apps.imaging.api.urls"),
    ),
]


# ============================================================
# 3. Remaining 149 DB-backed API
#
# 아직 개별 실제 View로 교체되지 않은 API를 처리한다.
# 위의 실제 구현 API보다 반드시 뒤에 위치해야 한다.
# ============================================================

urlpatterns += [
    path(
        "",
        include(
            "apps.ai_analysis.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.appointments.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.assessments.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.cdss.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.clinical_records.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.consultations.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.imaging.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.integrations.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.medication_safety.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.medications.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.notifications.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.prescriptions.api."
            "generated_real_149_urls"
        ),
    ),

    path(
        "",
        include(
            "apps.radiology.api."
            "generated_real_149_urls"
        ),
    ),
]


# ============================================================
# 4. 최종 API Contract Scaffold Fallback
#
# 위의 실제 구현 API와 DB-backed API에서 처리되지 않은
# 최종 API Contract 경로만 마지막 fallback으로 처리한다.
#
# 반드시 urlpatterns의 가장 마지막에 위치해야 한다.
# ============================================================

urlpatterns += [
    path(
        "",
        include(
            "config.contract_urls_generated"
        ),
    ),
]
