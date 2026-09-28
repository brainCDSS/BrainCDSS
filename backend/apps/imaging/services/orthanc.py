"""Small authenticated Orthanc REST client for backend and Celery workers."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


_ORTHANC_ID = re.compile(r"^[A-Za-z0-9-]{1,128}$")


class OrthancError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class OrthancUpload:
    orthanc_instance_id: str
    parent_series_id: str | None
    parent_study_id: str | None
    status: str


class OrthancClient:
    def __init__(self, *, base_url=None, username=None, password=None, timeout=None):
        self.base_url = (base_url or settings.ORTHANC_URL).rstrip("/")
        self.username = username if username is not None else settings.ORTHANC_USERNAME
        self.password = password if password is not None else settings.ORTHANC_PASSWORD
        self.timeout = timeout or settings.ORTHANC_TIMEOUT_SECONDS

    def system(self) -> dict:
        return self._json("GET", "/system")

    def get_study(self, study_id: str) -> dict:
        return self._json("GET", f"/studies/{self._id(study_id)}")

    def get_series(self, series_id: str) -> dict:
        return self._json("GET", f"/series/{self._id(series_id)}")

    def download_series_archive(self, series_id: str, destination: Path) -> Path:
        data = self._request("GET", f"/series/{self._id(series_id)}/archive")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return destination

    def upload_instance(self, dicom_path: Path) -> OrthancUpload:
        path = Path(dicom_path)
        if not path.is_file():
            raise OrthancError("DICOM_FILE_NOT_FOUND", "DICOM output file was not found")
        payload = self._json(
            "POST", "/instances", data=path.read_bytes(), content_type="application/dicom"
        )
        instance_id = payload.get("ID")
        if not instance_id:
            raise OrthancError("ORTHANC_INVALID_RESPONSE", "Orthanc upload response has no ID")
        return OrthancUpload(
            orthanc_instance_id=instance_id,
            parent_series_id=payload.get("ParentSeries"),
            parent_study_id=payload.get("ParentStudy"),
            status=payload.get("Status", "Success"),
        )

    def _json(self, method, path, *, data=None, content_type=None) -> dict:
        try:
            value = json.loads(self._request(method, path, data=data, content_type=content_type))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OrthancError("ORTHANC_INVALID_RESPONSE", "Orthanc returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise OrthancError("ORTHANC_INVALID_RESPONSE", "Orthanc returned an unexpected response")
        return value

    def _request(self, method, path, *, data=None, content_type=None) -> bytes:
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        if self.username or self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code == 404:
                code = "ORTHANC_RESOURCE_NOT_FOUND"
            elif exc.code in {401, 403}:
                code = "ORTHANC_AUTH_FAILED"
            else:
                code = "ORTHANC_HTTP_ERROR"
            raise OrthancError(code, f"Orthanc HTTP {exc.code}", retryable=exc.code >= 500) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise OrthancError("ORTHANC_UNAVAILABLE", "Orthanc is unavailable", retryable=True) from exc

    @staticmethod
    def _id(value: str) -> str:
        if not _ORTHANC_ID.fullmatch(value):
            raise OrthancError("ORTHANC_INVALID_ID", "Invalid Orthanc resource ID")
        return value
