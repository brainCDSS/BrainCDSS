from rest_framework.exceptions import (
    AuthenticationFailed,
)
from rest_framework.permissions import (
    BasePermission,
)

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.common.authentication import (
    ServiceAuthenticationUnavailable,
    ServiceJWTAuthentication,
)


class CDSServiceJWTAuthentication(
    ServiceJWTAuthentication
):
    """
    기존 BrainOn Service JWT 인증을 그대로 사용한다.

    CDS Hooks에서는 기존 METRICS_* 인증 오류명을
    CDS_* 오류명으로 변환한다.
    """

    def authenticate(
        self,
        request,
    ):
        try:
            return super().authenticate(
                request
            )

        except ServiceAuthenticationUnavailable as exc:
            raise ContractAPIException(
                "CDS_AUTH_UNAVAILABLE",
                (
                    "Service JWT authentication "
                    "is not configured."
                ),
                503,
            ) from exc

        except AuthenticationFailed as exc:
            raise ContractAPIException(
                "CDS_AUTH_REQUIRED",
                (
                    "Invalid or expired "
                    "Service JWT."
                ),
                401,
            ) from exc


class RequiredCDSServiceScopePermission(
    BasePermission
):
    """
    View의 required_service_scope와
    Service JWT scope를 비교한다.
    """

    def has_permission(
        self,
        request,
        view,
    ):
        principal = getattr(
            request,
            "user",
            None,
        )

        if not getattr(
            principal,
            "is_service",
            False,
        ):
            raise ContractAPIException(
                "CDS_AUTH_REQUIRED",
                (
                    "Service JWT "
                    "authentication is required."
                ),
                401,
            )

        required_scope = getattr(
            view,
            "required_service_scope",
            None,
        )

        if (
            required_scope
            and required_scope
            not in principal.scopes
        ):
            raise ContractAPIException(
                "CDS_FORBIDDEN",
                (
                    "Missing Service JWT scope: "
                    f"{required_scope}"
                ),
                403,
            )

        return True


try:
    from drf_spectacular.extensions import (
        OpenApiAuthenticationExtension,
    )

    class CDSServiceJWTAuthenticationScheme(
        OpenApiAuthenticationExtension
    ):
        target_class = (
            "apps.cdss.api."
            "cds_service_authentication."
            "CDSServiceJWTAuthentication"
        )

        name = "CDSServiceJWT"

        def get_security_definition(
            self,
            auto_schema,
        ):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": (
                    "BrainOn CDS Hooks Service JWT. "
                    "Endpoint-specific CDS scope required."
                ),
            }

except ImportError:
    pass
