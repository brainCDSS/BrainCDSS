from __future__ import annotations

import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials


def get_firebase_app():
    """
    BrainOn FCM용 Firebase Admin App을 반환한다.
    최초 호출 시 초기화하고 이후에는 기존 App을 재사용한다.
    """
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    project_id = os.getenv(
        "FCM_PROJECT_ID",
        "",
    ).strip()

    credentials_path = os.getenv(
        "FCM_CREDENTIALS_PATH",
        "",
    ).strip()

    if not project_id:
        raise RuntimeError(
            "FCM_PROJECT_ID_REQUIRED"
        )

    if not credentials_path:
        raise RuntimeError(
            "FCM_CREDENTIALS_PATH_REQUIRED"
        )

    path = Path(credentials_path)

    if not path.is_file():
        raise RuntimeError(
            "FCM_CREDENTIALS_FILE_NOT_FOUND"
        )

    credential = credentials.Certificate(
        str(path)
    )

    if credential.project_id != project_id:
        raise RuntimeError(
            "FCM_PROJECT_ID_MISMATCH"
        )

    return firebase_admin.initialize_app(
        credential,
        {
            "projectId": project_id,
        },
    )
