from rest_framework.exceptions import APIException


class AuditContractError(APIException):
    def __init__(
        self,
        code: str,
        detail: str,
        status_code: int,
    ):
        self.status_code = status_code
        self.default_code = code
        super().__init__({
            "code": code,
            "detail": detail,
        })
