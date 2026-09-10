# Standalone development inference mock

Implementation: `mocks/inference-server/main.py`. This is a synthetic development
contract, not the clinical API-AI-010 contract. No patient inputs, model execution,
database access, result persistence or external requests are performed.

| Endpoint | Input | Response |
| --- | --- | --- |
| GET `/health` | None | 200: `status: ok`, `service: inference-mock`, `is_mock: true` |
| GET `/ready` | None | Enabled: 200 `status: ready`, `mode: MOCK`, `is_mock: true`, `model_configured: false`; disabled: 503 `detail: MOCK_DISABLED` |
| POST `/mock/inference` | `analysis_id`: UUID; optional `outcome`: `success` (default) or `failure`; extra fields forbidden | Success: 200 response below; failure: 500 `detail: MOCK_INFERENCE_FAILED` |

```json
{
  "analysis_id": "00000000-0000-0000-0000-000000000001",
  "mode": "MOCK",
  "is_mock": true,
  "accuracy_simulated": false,
  "status": "SUCCEEDED",
  "result": {"message": "Synthetic pipeline verification only"}
}
```

Enable with `INFERENCE_MOCK_ENABLED=true`; default is disabled.
Valid inference requests return 404 `detail: MOCK_DISABLED` when disabled.
Invalid request bodies return 422 (validation can precede the disabled check).
The caller supplies the UUID; the mock only echoes it. `SUCCEEDED` describes
the mock response, never actual model readiness or medical accuracy.
There is no authentication. Compose exposes this development service on host
loopback only, port 8110. Contract tests: `mocks/inference-server/tests/test_api.py`.

## Django development bridge

The local-only Django bridge uses the existing `AIAnalysis`,
`AIAnalysisStatusHistory`, and `AIAnalysisResult` tables. It creates no mock
model or database migration. It is hidden with 404 unless
`AI_INFERENCE_DEVELOPMENT_ENABLED=true`.

`POST /api/v1/dev/ai-analyses` requires UUIDs for an AVAILABLE ImagingStudy,
an active ModelVersion, its active AIModelConfigVersion, and an active User.
It also accepts `analysis_type`, `priority`, and development-only
`outcome: success|failure`. It stores QUEUED, then publishes only the analysis
UUID and outcome to `apps.ai_analysis.run_analysis_inference` through RabbitMQ.

`GET /api/v1/dev/ai-analyses/{analysis_id}` returns the current status, stage,
failure code, attempt count, append-only status history, and the structured
mock result. Successful execution stores a non-clinical result with nullable
clinical measurements, `severity: MOCK`, `is_mock: true`, and
`accuracy_simulated: false`. Failed execution stores no AIAnalysisResult.

This bridge has no authentication and is for local synthetic verification
only. It does not replace the user-authorized clinical API-AI-001/003/004
flows, object-scope checks, input-series validation, audit, or outbox contract.
