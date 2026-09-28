"""Stable service errors mapped to the public inference contract."""


class InferenceServiceError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False, detail=None):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.detail = detail or {}


class ModelNotReadyError(InferenceServiceError):
    def __init__(self, message: str, *, detail=None):
        super().__init__("MODEL_NOT_READY", message, retryable=True, detail=detail)
