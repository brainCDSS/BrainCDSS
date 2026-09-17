"""Direct Vertex REST + ADC; no dependency on Assistant or MCP code paths."""
import hashlib
import json
import re
from pathlib import Path

import google.auth
from django.conf import settings
from google.auth.transport.requests import Request as AuthRequest

from .http import ExternalServiceError, request_bytes

SUMMARY_FIELDS = {
    "short_summary": "summary_short", "objective": "summary_objective",
    "population_and_methods": "summary_methods", "key_results": "summary_results",
    "clinical_significance": "summary_clinical_significance", "limitations": "summary_limitations",
}
PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "abstract_summary.txt").read_text(encoding="utf-8")


def input_hash(article):
    body = json.dumps({name: article[name] for name in ("title", "abstract", "publication_type")}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()


def parse_summary(text):
    try:
        result = json.loads(text)
    except (ValueError, TypeError):
        raise ExternalServiceError("SUMMARY_INVALID_JSON") from None
    if not isinstance(result, dict) or set(result) != set(SUMMARY_FIELDS):
        raise ExternalServiceError("SUMMARY_INVALID_FIELDS")
    for value in result.values():
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 6000):
            raise ExternalServiceError("SUMMARY_INVALID_VALUE")
    if not result["short_summary"]:
        raise ExternalServiceError("SUMMARY_MISSING_SHORT_SUMMARY")
    return {SUMMARY_FIELDS[key]: value for key, value in result.items()}


class VertexSummarizer:
    def __init__(self):
        self.model = settings.CLINICAL_EVIDENCE_GEMINI_MODEL
        self.version = settings.CLINICAL_EVIDENCE_SUMMARY_VERSION
        self._credentials = None

    def summarize(self, article):
        if not article["abstract"].strip():
            return None
        project = settings.CLINICAL_EVIDENCE_GCP_PROJECT
        location = settings.CLINICAL_EVIDENCE_GCP_LOCATION
        if not all(re.fullmatch(r"[A-Za-z0-9._-]+", value or "") for value in (project, location, self.model)):
            raise ExternalServiceError("MODEL_NOT_CONFIGURED")
        try:
            if self._credentials is None:
                self._credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            if not self._credentials.valid:
                self._credentials.refresh(AuthRequest())
        except Exception:
            raise ExternalServiceError("VERTEX_AUTH_UNAVAILABLE") from None
        host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
        url = f"https://{host}/v1/projects/{project}/locations/{location}/publishers/google/models/{self.model}:generateContent"
        source = {name: article[name] for name in ("title", "abstract", "publication_type")}
        payload = {
            "systemInstruction": {"parts": [{"text": PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(source, ensure_ascii=False)}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 2048,
                "responseMimeType": "application/json", "responseSchema": {
                    "type": "OBJECT", "required": list(SUMMARY_FIELDS),
                    "properties": {key: {"type": "STRING", "nullable": True} for key in SUMMARY_FIELDS},
                }},
        }
        body = request_bytes(url, data=json.dumps(payload).encode(), headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self._credentials.token}"},
            timeout=settings.CLINICAL_EVIDENCE_HTTP_TIMEOUT)
        try:
            response = json.loads(body)
            candidate = response["candidates"][0]
            if candidate.get("finishReason") != "STOP":
                raise ValueError("Incomplete generation")
            text = "".join(part.get("text", "") for part in candidate["content"]["parts"] if not part.get("thought"))
        except (ValueError, KeyError, IndexError, TypeError):
            raise ExternalServiceError("VERTEX_INVALID_RESPONSE") from None
        return parse_summary(text)
