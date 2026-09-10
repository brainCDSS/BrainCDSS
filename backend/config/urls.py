"""Root HTTP routes for the BrainOn backend."""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.common.views import health


urlpatterns = [
    path("api/v1/", include("apps.organizations.api.urls")),
    path("api/v1/", include("apps.patients.api.urls")),
    path(
        "api/v1/health/",
        health,
        name="health",
    ),

    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="openapi-schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="openapi-schema"
        ),
        name="swagger-ui",
    ),
]


# BEGIN BRAINON ACCOUNTS REAL API ROUTES
# Actual implementation for accounts final contract APIs.
# This block MUST stay before generated 501 scaffold routes.
from django.urls import include as _brainon_accounts_include
from django.urls import path as _brainon_accounts_path

urlpatterns += [
    _brainon_accounts_path(
        "",
        _brainon_accounts_include(
            "apps.accounts.api.urls"
        ),
    ),
]
# END BRAINON ACCOUNTS REAL API ROUTES

# BEGIN BRAINON COMMON AUDIT REAL API ROUTES
# Actual implementation for Phase 1 common/audit contract APIs.
# This block MUST stay before generated scaffold routes.
from django.urls import include as _brainon_ca_include
from django.urls import path as _brainon_ca_path

urlpatterns += [
    _brainon_ca_path(
        "",
        _brainon_ca_include(
            "apps.audit.api.urls"
        ),
    ),
    _brainon_ca_path(
        "",
        _brainon_ca_include(
            "apps.common.api.urls"
        ),
    ),
]
# END BRAINON COMMON AUDIT REAL API ROUTES

# BEGIN BRAINON MEDICATION SAFETY REAL API ROUTES
# Real DUR API must stay before generated remaining-149 routes.
urlpatterns += [
    path(
        "",
        include(
            "apps.medication_safety.api.urls"
        ),
    ),
]
# END BRAINON MEDICATION SAFETY REAL API ROUTES

# BEGIN BRAINON PRESCRIPTIONS REAL API ROUTES
# Actual prescription finalize implementation.
# Must stay before generated remaining-149 routes.
urlpatterns += [
    path(
        "",
        include(
            "apps.prescriptions.api.urls"
        ),
    ),
]
# END BRAINON PRESCRIPTIONS REAL API ROUTES

# BEGIN BRAINON CDS HOOKS REAL API ROUTES
# Actual CDS Hooks API-CDS-001~003.
# Must stay before generated remaining-149 routes.
urlpatterns += [
    path(
        "",
        include(
            "apps.cdss.api.urls"
        ),
    ),
]
# END BRAINON CDS HOOKS REAL API ROUTES

# BEGIN BRAINON REMAINING 149 REAL ROUTES
# Generated DB-backed routes for the remaining 149 contract APIs.
# Keep this block before the legacy generated scaffold routes.
from django.urls import include as _brainon_r149_include
from django.urls import path as _brainon_r149_path

urlpatterns += [
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.ai_analysis.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.appointments.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.assessments.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.cdss.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.clinical_records.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.consultations.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.imaging.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.integrations.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.medication_safety.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.medications.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.notifications.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.prescriptions.api.generated_real_149_urls"
        ),
    ),
    _brainon_r149_path(
        "",
        _brainon_r149_include(
            "apps.radiology.api.generated_real_149_urls"
        ),
    ),
]
# END BRAINON REMAINING 149 REAL ROUTES
# BEGIN BRAINON GENERATED FINAL API CONTRACT ROUTES
# Temporary scaffold for the final 176 API contract.
# Real API implementations replace these generated handlers.
from django.urls import include as _brainon_include
from django.urls import path as _brainon_path

urlpatterns += [
    _brainon_path(
        "",
        _brainon_include(
            "config.contract_urls_generated"
        ),
    ),
]
# END BRAINON GENERATED FINAL API CONTRACT ROUTES

