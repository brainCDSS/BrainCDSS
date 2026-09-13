"""Celery orchestration for the private production inference service."""

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import AIAnalysis, AIAnalysisAttempt
from apps.audit.services.audit_event import record_audit_event
from apps.ai_analysis.services.inference import store_inference_result, transition_analysis
from apps.ai_analysis.services.inference_client import InferenceClientError, call_inference


logger = logging.getLogger(__name__)


def _record_terminal_audit(
    analysis,
    *,
    action,
    outcome,
    reason=None,
):
    """
    Persist the terminal AI analysis audit event using the
    original HTTP correlation identifier.

    Celery has no Django HttpRequest, so the original
    AIAnalysis.trace is supplied explicitly as request_id.
    """

    record_audit_event(
        source_service="backend.ai_analysis.worker",
        action=action,
        resource_type="AIAnalysis",
        outcome=outcome,
        request_id=analysis.trace,
        actor_user=analysis.requested_by,
        resource_id=analysis.id,
        patient_id=analysis.study.patient_id,
        reason=reason,
        after_json={
            "analysis_id":
                str(analysis.id),
            "status":
                analysis.status,
            "stage":
                analysis.stage,
            "failure_code":
                analysis.failure_code,
            "trace_id":
                analysis.trace,
        },
    )


ROLE_ORDER = {
    "HEMORRHAGIC_STROKE_CT": {"CT": 0},
    "ISCHEMIC_STROKE_DWI_ADC": {"DWI": 0, "ADC": 1},
    "CEREBRAL_ANEURYSM_MRA": {"MRA": 0},
}

@shared_task(
    bind=True,
    name="apps.ai_analysis.run_analysis_inference",
    ignore_result=True,
    max_retries=2,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_analysis_inference(self, analysis_id):
    with transaction.atomic():
        analysis = (
            AIAnalysis.objects.select_for_update()
            .select_related("model_version__model")
            .get(pk=analysis_id)
        )
        if analysis.status not in {"QUEUED", "RETRYING"}:
            return

        task_headers = (
            getattr(
                self.request,
                "headers",
                None,
            )
            or {}
        )

        logger.info(
            "AI_INFERENCE_CORRELATION "
            "analysis_id=%s "
            "analysis_trace=%s "
            "request_id=%s "
            "trace_id=%s",
            analysis.id,
            analysis.trace,
            task_headers.get(
                "request_id"
            ),
            task_headers.get(
                "trace_id"
            ),
        )

        analysis.attempt_count += 1
        attempt_number = analysis.attempt_count
        transition_analysis(analysis, status="PROCESSING", stage="PREPARING")
        attempt = AIAnalysisAttempt.objects.create(
            analysis=analysis,
            attempt_number=attempt_number,
            status="PROCESSING",
            stage="PREPARING",
            started_at=timezone.now(),
            finished_at=None,
            error_code=None,
            trace=analysis.trace,
        )

    try:
        payload = build_inference_payload(analysis, attempt_number)
        response = call_inference(payload)
        if response.get("status") != "SUCCEEDED":
            error = response.get("error") or {}
            raise InferenceClientError(
                error.get("code", "INFERENCE_FAILED"),
                error.get("message", "inference failed"),
                retryable=bool(error.get("retryable")),
            )
        _validate_success_response(
            response,
            analysis.trace,
        )
    except InferenceClientError as exc:
        _finish_failed_attempt(analysis_id, attempt.id, exc.code)
        if exc.retryable and self.request.retries < self.max_retries:
            with transaction.atomic():
                locked = AIAnalysis.objects.select_for_update().get(pk=analysis_id)
                transition_analysis(
                    locked, status="RETRYING", stage="PREPARING", reason_code=exc.code
                )
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        with transaction.atomic():
            locked = (
                AIAnalysis.objects
                .select_for_update()
                .select_related(
                    "requested_by",
                    "study",
                )
                .get(pk=analysis_id)
            )

            transition_analysis(
                locked,
                status="FAILED",
                stage="FINALIZING",
                reason_code=exc.code,
            )

            _record_terminal_audit(
                locked,
                action="AI_ANALYSIS_FAILED",
                outcome="FAILURE",
                reason=exc.code,
            )

        return

    with transaction.atomic():
        locked = (
            AIAnalysis.objects
            .select_for_update()
            .select_related(
                "requested_by",
                "study",
            )
            .get(pk=analysis_id)
        )

        transition_analysis(
            locked,
            status="PROCESSING",
            stage="POSTPROCESSING",
        )

        store_inference_result(
            locked,
            response,
        )

        transition_analysis(
            locked,
            status="COMPLETED",
            stage="FINALIZING",
        )

        AIAnalysisAttempt.objects.filter(
            pk=attempt.id
        ).update(
            status="COMPLETED",
            stage="FINALIZING",
            finished_at=timezone.now(),
            error_code=None,
        )

        _record_terminal_audit(
            locked,
            action="AI_ANALYSIS_COMPLETED",
            outcome="SUCCESS",
        )


def build_inference_payload(analysis, attempt_number):
    order = ROLE_ORDER.get(analysis.analysis_type)
    if order is None:
        raise InferenceClientError("UNSUPPORTED_ANALYSIS_TYPE", "unsupported analysis type")
    inputs = list(analysis.input_artifacts.values("role", "uri", "size_bytes", "sha256"))
    if {item["role"] for item in inputs} != set(order):
        raise InferenceClientError("INVALID_REQUEST", "analysis input roles are incomplete")
    inputs.sort(key=lambda item: order[item["role"]])
    version = analysis.model_version
    return {
        "analysis_id": str(analysis.id),
        "analysis_type": analysis.analysis_type,
        "attempt": attempt_number,
        "trace_id": analysis.trace,
        "model_selector": {
            "name": version.model.code,
            "version": version.version,
            "manifest_uri": version.artifact_uri,
        },
        "inputs": inputs,
    }


def _validate_success_response(
    response,
    expected_trace_id,
):
    response_trace_id = str(
        response.get("trace_id")
        or ""
    )

    if response_trace_id != str(
        expected_trace_id
    ):
        raise InferenceClientError(
            "INFERENCE_TRACE_MISMATCH",
            "Cloud Run inference trace_id "
            "does not match the BrainOn request_id",
            retryable=False,
        )

    output_types = {item.get("type") for item in response.get("outputs", [])}
    if output_types != {"NIFTI_MASK", "RESULT_JSON"}:
        raise InferenceClientError("INVALID_INFERENCE_RESPONSE", "required outputs are missing")
    for output in response["outputs"]:
        if not output.get("uri", "").startswith("gs://") or not output.get("sha256"):
            raise InferenceClientError("INVALID_INFERENCE_RESPONSE", "invalid output metadata")


def _finish_failed_attempt(analysis_id, attempt_id, code):
    AIAnalysisAttempt.objects.filter(pk=attempt_id, analysis_id=analysis_id).update(
        status="FAILED",
        stage="FINALIZING",
        finished_at=timezone.now(),
        error_code=code,
    )
