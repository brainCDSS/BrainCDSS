from rest_framework.exceptions import APIException


class ContractAPIException(APIException):
    def __init__(
        self,
        code: str,
        detail: str,
        status_code: int,
    ):
        self.status_code = status_code

        super().__init__(
            detail={
                "code": code,
                "detail": detail,
            },
            code=code,
        )
