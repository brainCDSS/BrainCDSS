"""Maps DRF errors to the common contract envelope."""

from rest_framework.views import exception_handler

from apps.common.tracking import build_tracking_code


def api_exception_handler(
    exc,
    context,
):
    response = exception_handler(
        exc,
        context,
    )

    if response is None:
        return None

    request = context.get(
        "request"
    )

    request_id = getattr(
        request,
        "request_id",
        "",
    )

    tracking_code = (
        build_tracking_code(
            request_id
        )
    )

    response.data = {
        "error": {
            "code": getattr(
                exc,
                "default_code",
                "API_ERROR",
            ),
            "message": (
                "요청을 처리하지 못했습니다."
            ),
            "details": response.data,
        },

        # 사용자/운영자 문의용
        "tracking_code":
            tracking_code,

        # 기존 API 호환용.
        # 사용자 UI에서는 표시하지 않는다.
        "trace_id":
            request_id,
    }

    return response
