from rest_framework.exceptions import APIException


class MetricsForbidden(APIException):
    status_code = 403
    default_code = "METRICS_FORBIDDEN"
    default_detail = {
        "code": "METRICS_FORBIDDEN",
        "detail": "Required service scope is missing.",
    }


class MetricsUnavailable(APIException):
    status_code = 503
    default_code = "METRICS_UNAVAILABLE"
    default_detail = {
        "code": "METRICS_UNAVAILABLE",
        "detail": "Metrics are unavailable.",
    }
