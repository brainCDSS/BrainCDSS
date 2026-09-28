from rest_framework.exceptions import APIException


class DomainAPIException(APIException):
    status_code = 400
    default_code = "DOMAIN_ERROR"

    def __init__(self, *, code: str, detail: str, status_code: int):
        self.status_code = status_code
        self.default_code = code
        super().__init__({
            "code": code,
            "detail": detail,
        })
