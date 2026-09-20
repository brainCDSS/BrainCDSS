#!/bin/sh
set -e

ENCODED_PASSWORD=$(python -c "import os, urllib.parse; print(urllib.parse.quote(os.environ['MLFLOW_DB_PASSWORD'], safe=''))")

export MLFLOW_BACKEND_STORE_URI="postgresql+psycopg2://${MLFLOW_DB_USER}:${ENCODED_PASSWORD}@/${MLFLOW_DB_NAME}?host=/cloudsql/${CLOUD_SQL_CONNECTION_NAME}"

exec mlflow server \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --workers 1 \
  --backend-store-uri "$MLFLOW_BACKEND_STORE_URI" \
  --artifacts-destination "$MLFLOW_ARTIFACT_ROOT"