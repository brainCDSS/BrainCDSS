#!/usr/bin/env bash

CONTAINER="brainon-backend-api"
KEY_FILE="/opt/brainon/secrets/service-jwt.key"
HEALTH_URL="http://127.0.0.1:8080/api/v1/health/"
INTERVAL=15


ensure_service_jwt() {

    if [ ! -s "$KEY_FILE" ]; then
        echo "SERVICE_JWT_GUARD=SECRET_FILE_MISSING"
        return 1
    fi


    STATE="$(
        docker inspect \
          "$CONTAINER" \
          --format '{{.State.Status}}' \
          2>/dev/null
    )"


    if [ "$STATE" != "running" ]; then
        echo "SERVICE_JWT_GUARD=WAITING_FOR_CONTAINER"
        return 0
    fi


    docker cp \
      "$KEY_FILE" \
      "$CONTAINER:/tmp/brainon-service-jwt.key" \
      >/dev/null 2>&1


    if [ "$?" != "0" ]; then
        echo "SERVICE_JWT_GUARD=COPY_FAIL"
        return 1
    fi


    RESULT="$(
        docker exec \
          -u 0 \
          "$CONTAINER" \
          python -c '
import json
import os
from pathlib import Path

key_path = Path("/tmp/brainon-service-jwt.key")
env_path = Path("/.env")

key = key_path.read_text(
    encoding="utf-8"
).strip()

if not key:
    raise RuntimeError(
        "SERVICE_JWT_KEY_EMPTY"
    )

existing = (
    env_path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    if env_path.exists()
    else ""
)

managed = {
    "SERVICE_JWT_SIGNING_KEY",
    "SERVICE_JWT_ALGORITHM",
    "SERVICE_JWT_ISSUER",
    "SERVICE_JWT_AUDIENCE",
}

actual = ""

for line in existing.splitlines():

    if line.startswith(
        "SERVICE_JWT_SIGNING_KEY="
    ):

        raw = line.split(
            "=",
            1,
        )[1].strip()

        try:
            actual = json.loads(raw)

        except Exception:
            actual = (
                raw
                .strip(chr(34))
                .strip(chr(39))
            )

        break


if actual == key:

    print("ALREADY")

else:

    kept = []

    for line in existing.splitlines():

        if "=" in line:
            name = (
                line
                .split("=", 1)[0]
                .strip()
            )
        else:
            name = ""

        if name in managed:
            continue

        kept.append(line)


    kept.extend([
        "",
        "# BrainOn internal Service JWT",
        (
            "SERVICE_JWT_SIGNING_KEY="
            + json.dumps(key)
        ),
        "SERVICE_JWT_ALGORITHM=HS256",
        "SERVICE_JWT_ISSUER=brainon-internal",
        (
            "SERVICE_JWT_AUDIENCE="
            "brainon-django-internal"
        ),
    ])


    env_path.write_text(
        "\n".join(kept).rstrip()
        + "\n",
        encoding="utf-8",
    )

    os.chmod(
        env_path,
        0o600,
    )

    print("UPDATED")
' \
          2>/dev/null
    )"


    PYTHON_RC="$?"


    docker exec \
      -u 0 \
      "$CONTAINER" \
      rm -f \
      /tmp/brainon-service-jwt.key \
      >/dev/null 2>&1 \
      || true


    if [ "$PYTHON_RC" != "0" ]; then
        echo "SERVICE_JWT_GUARD=ENV_CHECK_FAIL"
        return 1
    fi


    if [ "$RESULT" = "ALREADY" ]; then
        echo "SERVICE_JWT_GUARD=CONFIGURED"
        return 0
    fi


    if [ "$RESULT" != "UPDATED" ]; then
        echo "SERVICE_JWT_GUARD=UNKNOWN_RESULT"
        return 1
    fi


    echo "SERVICE_JWT_GUARD=INJECTED"


    docker restart \
      "$CONTAINER" \
      >/dev/null


    HEALTH="000"


    for i in $(seq 1 30)
    do

        HEALTH="$(
            curl -sS \
              -o /tmp/brainon-jwt-health \
              -w "%{http_code}" \
              "$HEALTH_URL" \
              2>/dev/null
        )"


        if [ "$HEALTH" = "200" ]; then
            break
        fi


        sleep 2

    done


    rm -f \
      /tmp/brainon-jwt-health


    if [ "$HEALTH" = "200" ]; then
        echo "SERVICE_JWT_GUARD=BACKEND_READY"
        return 0
    fi


    echo "SERVICE_JWT_GUARD=BACKEND_NOT_READY"

    return 1
}


echo "SERVICE_JWT_GUARD=STARTED"


while true
do

    ensure_service_jwt

    sleep "$INTERVAL"

done
