# MLflow Registry synchronization API

## `POST /api/v1/admin/ml/mlflow/sync`

System administrators only. The backend obtains a Google-signed Cloud Run ID
token when the request runs and uses it only to read the configured private
MLflow Registry. It never stores a token or service-account key.

Response:

```json
{
  "discovered": 5,
  "created": 2,
  "updated": 3,
  "skipped": 0,
  "errors": 0,
  "error_details": []
}
```

The idempotency key is `mlflow_registered_model_name + mlflow_model_version`.
Existing rows receive MLflow metadata updates only. New rows are always
`validation_status=DRAFT` and `is_active=false`.

This endpoint never validates or approves a model, activates a model/config,
or changes production routing. A Registry model must map uniquely to an
existing BrainCDSS AIModel through an existing MLflow model name or exact
AIModel code/display name. Unknown mappings are returned as errors; no AIModel
is guessed or created automatically.
