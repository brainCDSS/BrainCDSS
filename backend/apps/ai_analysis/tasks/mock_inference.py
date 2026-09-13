"""Celery bridge retained for the explicitly enabled local mock API."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from celery import shared_task
from django.conf import settings
from django.db import transaction

from apps.ai_analysis.models import AIAnalysis
from apps.ai_analysis.services.inference import store_mock_result, transition_analysis


@shared_task(name="apps.ai_analysis.run_mock_analysis_inference", ignore_result=True)
def run_mock_analysis_inference(analysis_id, outcome="success"):
    if not settings.AI_INFERENCE_DEVELOPMENT_ENABLED:
        return
    with transaction.atomic():
        analysis = AIAnalysis.objects.select_for_update().get(pk=analysis_id)
        if analysis.status != "QUEUED":
            return
        analysis.attempt_count += 1
        transition_analysis(analysis, status="PROCESSING", stage="INFERENCE")
    response = None
    failure_code = None
    try:
        request = Request(
            settings.INFERENCE_API_URL.rstrip("/") + "/mock/inference",
            data=json.dumps({"analysis_id": str(analysis.id), "outcome": outcome}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=settings.INFERENCE_TIMEOUT_SECONDS) as http_response:
            response = json.load(http_response)
        if not isinstance(response, dict) or response.get("analysis_id") != str(analysis.id) or response.get("is_mock") is not True or response.get("status") != "SUCCEEDED":
            response = None
            failure_code = "INVALID_INFERENCE_RESPONSE"
    except HTTPError as exc:
        failure_code = "MOCK_INFERENCE_FAILED" if exc.code == 500 else "INFERENCE_HTTP_ERROR"
    except (URLError, TimeoutError, OSError):
        failure_code = "INFERENCE_UNAVAILABLE"
    except (TypeError, ValueError):
        failure_code = "INVALID_INFERENCE_RESPONSE"
    with transaction.atomic():
        analysis = AIAnalysis.objects.select_for_update().get(pk=analysis_id)
        if failure_code:
            transition_analysis(analysis, status="FAILED", stage="FINALIZING", reason_code=failure_code)
        else:
            store_mock_result(analysis, response)
            transition_analysis(analysis, status="COMPLETED", stage="FINALIZING")
