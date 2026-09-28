"""MOSEC routes that isolate the three clinical model workloads."""

from __future__ import annotations

import logging
import os

from mosec import Server, Worker

from src.errors import InferenceServiceError
from src.runtime import get_service
from src.schemas import AnalysisType, InferenceError, InferenceRequest, InferenceResponse


logger = logging.getLogger(__name__)


class ModelWorker(Worker):
    analysis_type: AnalysisType

    def forward(self, data):
        request = InferenceRequest.model_validate(data)

        if request.analysis_type != self.analysis_type:
            return _failure(
                request,
                "MODEL_ROUTE_MISMATCH",
                False,
            )

        try:
            return get_service().execute(request).model_dump(mode="json")

        except InferenceServiceError as exc:
            return _failure(
                request,
                exc.code,
                exc.retryable,
                str(exc),
                exc.detail,
            )

        except Exception as exc:
            logger.exception(
                "Unhandled model worker exception | "
                "analysis_id=%s | analysis_type=%s | model=%s | version=%s",
                request.analysis_id,
                request.analysis_type,
                request.model_selector.name,
                request.model_selector.version,
            )

            return _failure(
                request,
                "INTERNAL_ERROR",
                False,
                message=f"{type(exc).__name__}: {exc}",
            )
        finally:
            # Keep only the current request's model on the GPU. Without this,
            # the three MOSEC workers retain their model caches and leave no
            # headroom for gradient-based XAI.
            get_service().release_predictors()


class HemorrhageWorker(ModelWorker):
    analysis_type = AnalysisType.HEMORRHAGIC_STROKE_CT


class IschemiaWorker(ModelWorker):
    analysis_type = AnalysisType.ISCHEMIC_STROKE_DWI_ADC


class AneurysmWorker(ModelWorker):
    analysis_type = AnalysisType.CEREBRAL_ANEURYSM_MRA


WORKER_ROUTES = {
    "hemorrhage": (
        HemorrhageWorker,
        "/v1/models/hemorrhage",
    ),
    "ischemia": (
        IschemiaWorker,
        "/v1/models/ischemia",
    ),
    "aneurysm": (
        AneurysmWorker,
        "/v1/models/aneurysm",
    ),
}


def build_server() -> Server:
    enabled = {
        item.strip()
        for item in os.getenv(
            "MOSEC_ENABLED_MODELS",
            "hemorrhage,ischemia,aneurysm",
        ).split(",")
        if item.strip()
    }

    unknown = enabled - WORKER_ROUTES.keys()

    if unknown:
        raise RuntimeError(
            f"unknown MOSEC model routes: {sorted(unknown)}"
        )

    server = Server()

    timeout = float(
        os.getenv(
            "MOSEC_WORKER_TIMEOUT_SECONDS",
            "1800",
        )
    )

    for name, (worker, route) in WORKER_ROUTES.items():
        if name in enabled:
            server.append_worker(
                worker,
                num=1,
                max_batch_size=1,
                max_wait_time=0,
                timeout=timeout,
                route=route,
            )

    return server


def _failure(
    request,
    code,
    retryable,
    message="model worker failed",
    detail=None,
):
    return InferenceResponse(
        analysis_id=request.analysis_id,
        analysis_type=request.analysis_type,
        attempt=request.attempt,
        status="FAILED",
        outputs=[],
        metrics={},
        timing_ms={},
        model=None,
        error=InferenceError(
            code=code,
            message=message,
            retryable=retryable,
            detail=detail or {},
        ),
        trace_id=request.trace_id or "missing-trace-id",
    ).model_dump(mode="json")


if __name__ == "__main__":
    build_server().run()
