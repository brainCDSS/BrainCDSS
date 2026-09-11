from dataclasses import dataclass

import jwt

from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from apps.accounts.api.errors import ContractAPIException
from apps.accounts.models import RolePermission
from apps.common.authentication import (
    ServiceAuthenticationUnavailable,
    ServiceJWTAuthentication,
)
from apps.imaging.services.viewer_session import (
    VIEWER_AUDIENCE,
    VIEWER_ISSUER,
    _viewer_signing_key,
)


class ImagingServiceJWTAuthentication(
    ServiceJWTAuthentication
):
    def authenticate(self, request):
        try:
            return super().authenticate(request)

        except ServiceAuthenticationUnavailable as exc:
            raise ContractAPIException(
                "SERVICE_AUTH_UNAVAILABLE",
                "Service JWT authentication is not configured.",
                503,
            ) from exc

        except AuthenticationFailed as exc:
            raise ContractAPIException(
                "SERVICE_AUTH_REQUIRED",
                "Invalid or expired Service JWT.",
                401,
            ) from exc


class RequiredImagingServiceScopePermission(
    BasePermission
):
    def has_permission(self, request, view):
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
                "SERVICE_AUTH_REQUIRED",
                "Service JWT authentication is required.",
                401,
            )

        required = getattr(
            view,
            "required_service_scope",
            None,
        )

        if (
            required
            and required not in principal.scopes
        ):
            raise ContractAPIException(
                "SERVICE_SCOPE_FORBIDDEN",
                f"Missing Service JWT scope: {required}",
                403,
            )

        return True


class ImagingAdminRetryPermission(
    BasePermission
):
    def has_permission(self, request, view):
        user = getattr(
            request,
            "user",
            None,
        )

        if (
            user is None
            or not getattr(user, "is_authenticated", False)
            or not getattr(user, "is_active", False)
            or getattr(
                getattr(user, "role", None),
                "code",
                None,
            ) != "SYSTEM_ADMIN"
        ):
            return False

        return RolePermission.objects.filter(
            role=user.role,
            permission__code="integration.retry",
        ).exists()


class ImagingNursePermission(
    BasePermission
):
    def has_permission(self, request, view):
        user = getattr(
            request,
            "user",
            None,
        )

        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_active", False)
            and getattr(
                getattr(user, "role", None),
                "code",
                None,
            ) == "NURSE"
        )


@dataclass(frozen=True)
class ViewerPrincipal:
    subject: str
    scopes: frozenset[str]
    claims: dict

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_service(self):
        return False


class ViewerJWTAuthentication(
    BaseAuthentication
):
    keyword = b"bearer"

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        auth = get_authorization_header(
            request
        ).split()

        if not auth:
            return None

        if (
            len(auth) != 2
            or auth[0].lower() != self.keyword
        ):
            raise ContractAPIException(
                "VIEWER_TOKEN_INVALID",
                "Invalid Viewer Authorization header.",
                401,
            )

        try:
            token = auth[1].decode("utf-8")

            claims = jwt.decode(
                token,
                _viewer_signing_key(),
                algorithms=["HS256"],
                issuer=VIEWER_ISSUER,
                audience=VIEWER_AUDIENCE,
            )

        except (
            UnicodeError,
            jwt.PyJWTError,
        ) as exc:
            raise ContractAPIException(
                "VIEWER_TOKEN_INVALID",
                "Invalid or expired Viewer token.",
                401,
            ) from exc

        if claims.get("token_type") != "viewer":
            raise ContractAPIException(
                "VIEWER_TOKEN_INVALID",
                "token_type must be viewer.",
                401,
            )

        raw_scope = claims.get(
            "scope",
            "",
        )

        scopes = frozenset(
            str(raw_scope).split()
        )

        principal = ViewerPrincipal(
            subject=str(
                claims.get("sub") or ""
            ),
            scopes=scopes,
            claims=claims,
        )

        request.viewer_claims = claims

        return principal, claims


class ViewerDicomReadPermission(
    BasePermission
):
    def has_permission(self, request, view):
        principal = getattr(
            request,
            "user",
            None,
        )

        if not isinstance(
            principal,
            ViewerPrincipal,
        ):
            raise ContractAPIException(
                "VIEWER_TOKEN_INVALID",
                "Viewer token is required.",
                401,
            )

        if "dicomweb.read" not in principal.scopes:
            raise ContractAPIException(
                "DICOM_SCOPE_FORBIDDEN",
                "dicomweb.read scope is required.",
                403,
            )

        return True


try:
    from drf_spectacular.extensions import (
        OpenApiAuthenticationExtension,
    )

    class ImagingServiceJWTScheme(
        OpenApiAuthenticationExtension
    ):
        target_class = (
            "apps.imaging.api."
            "imaging_remaining_auth."
            "ImagingServiceJWTAuthentication"
        )
        name = "ImagingServiceJWT"

        def get_security_definition(
            self,
            auto_schema,
        ):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }


    class ViewerJWTScheme(
        OpenApiAuthenticationExtension
    ):
        target_class = (
            "apps.imaging.api."
            "imaging_remaining_auth."
            "ViewerJWTAuthentication"
        )
        name = "ViewerJWT"

        def get_security_definition(
            self,
            auto_schema,
        ):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }

except ImportError:
    pass
