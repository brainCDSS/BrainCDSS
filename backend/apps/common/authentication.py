from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from django.conf import settings
from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
)


class ServiceAuthenticationUnavailable(APIException):
    status_code = 503
    default_code = "METRICS_UNAVAILABLE"
    default_detail = {
        "code": "METRICS_UNAVAILABLE",
        "detail": "Service JWT authentication is not configured.",
    }


@dataclass(frozen=True)
class ServicePrincipal:
    service_name: str
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
        return True

    def __str__(self):
        return self.service_name


def _setting(name: str, default=None):
    value = getattr(settings, name, None)
    if value not in (None, ""):
        return value

    value = os.environ.get(name)
    if value not in (None, ""):
        return value

    return default


def _scopes_from_claims(claims: dict) -> frozenset[str]:
    raw = claims.get("scope")

    if raw is None:
        raw = claims.get("scopes")

    if isinstance(raw, str):
        return frozenset(
            scope
            for scope in raw.split()
            if scope
        )

    if isinstance(raw, (list, tuple, set)):
        return frozenset(
            str(scope)
            for scope in raw
            if str(scope)
        )

    return frozenset()


class ServiceJWTAuthentication(BaseAuthentication):
    """
    BrainOn internal service authentication.

    User JWT and Service JWT deliberately use separate signing keys.
    Required production claims:
      token_type=service
      sub=<service-name>
      scope="scope.one scope.two"
      iat / exp
    """

    keyword = b"bearer"

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth:
            return None

        if auth[0].lower() != self.keyword:
            return None

        if len(auth) != 2:
            raise AuthenticationFailed({
                "code": "METRICS_AUTH_FAILED",
                "detail": "Invalid Authorization header.",
            })

        try:
            token = auth[1].decode("utf-8")
        except UnicodeError as exc:
            raise AuthenticationFailed({
                "code": "METRICS_AUTH_FAILED",
                "detail": "Invalid bearer token encoding.",
            }) from exc

        signing_key = _setting(
            "SERVICE_JWT_SIGNING_KEY"
        )

        if not signing_key:
            raise ServiceAuthenticationUnavailable()

        algorithm = _setting(
            "SERVICE_JWT_ALGORITHM",
            "HS256",
        )

        issuer = _setting(
            "SERVICE_JWT_ISSUER",
            "brainon-internal",
        )

        audience = _setting(
            "SERVICE_JWT_AUDIENCE",
            "brainon-django-internal",
        )

        try:
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                issuer=issuer,
                audience=audience,
                options={
                    "require": [
                        "exp",
                        "iat",
                        "sub",
                    ],
                },
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed({
                "code": "METRICS_AUTH_FAILED",
                "detail": "Invalid or expired Service JWT.",
            }) from exc

        if claims.get("token_type") != "service":
            raise AuthenticationFailed({
                "code": "METRICS_AUTH_FAILED",
                "detail": "token_type must be service.",
            })

        service_name = str(
            claims.get("sub") or ""
        ).strip()

        if not service_name:
            raise AuthenticationFailed({
                "code": "METRICS_AUTH_FAILED",
                "detail": "Service JWT subject is required.",
            })

        principal = ServicePrincipal(
            service_name=service_name,
            scopes=_scopes_from_claims(claims),
            claims=claims,
        )

        request.service_principal = principal

        return principal, claims


try:
    from drf_spectacular.extensions import (
        OpenApiAuthenticationExtension,
    )

    class ServiceJWTAuthenticationScheme(
        OpenApiAuthenticationExtension
    ):
        target_class = (
            "apps.common.authentication."
            "ServiceJWTAuthentication"
        )
        name = "ServiceJWT"

        def get_security_definition(self, auto_schema):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": (
                    "Internal BrainOn Service JWT. "
                    "Required scope is endpoint-specific."
                ),
            }

except ImportError:
    pass
