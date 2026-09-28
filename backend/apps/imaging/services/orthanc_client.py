from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.parse import (
    quote,
    urlencode,
)
from urllib.request import (
    Request,
    urlopen,
)

from django.utils import timezone


class OrthancUnavailable(Exception):
    pass


def _base_url():
    return os.getenv(
        "ORTHANC_BASE_URL",
        "http://127.0.0.1:8042",
    ).rstrip("/")


def _dicomweb_base_url():
    return os.getenv(
        "ORTHANC_DICOMWEB_BASE_URL",
        _base_url() + "/dicom-web",
    ).rstrip("/")


def _auth_header():
    username = os.getenv(
        "ORTHANC_USERNAME"
    )
    password = os.getenv(
        "ORTHANC_PASSWORD"
    )

    if not username:
        return None

    raw = (
        f"{username}:{password or ''}"
        .encode("utf-8")
    )

    return (
        "Basic "
        + base64.b64encode(raw).decode(
            "ascii"
        )
    )


def _timeout():
    try:
        return float(
            os.getenv(
                "ORTHANC_TIMEOUT_SECONDS",
                "5",
            )
        )
    except ValueError:
        return 5.0


def _json_request(
    url,
    *,
    accept="application/json",
):
    headers = {
        "Accept": accept,
        "User-Agent": "BrainOn-CDSS",
    }

    authorization = _auth_header()

    if authorization:
        headers["Authorization"] = authorization

    request = Request(
        url,
        headers=headers,
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=_timeout(),
        ) as response:
            raw = response.read().decode(
                "utf-8"
            )

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
    ) as exc:
        raise OrthancUnavailable(
            str(exc)
        ) from exc

    try:
        return json.loads(raw)

    except json.JSONDecodeError as exc:
        raise OrthancUnavailable(
            "Orthanc returned invalid JSON."
        ) from exc


def _int(value, default=None):
    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _decimal(value):
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def _study_datetime(tags):
    date = str(
        tags.get("StudyDate") or ""
    ).strip()

    time = str(
        tags.get("StudyTime") or ""
    ).strip()

    if len(date) != 8:
        return None

    clean_time = (
        time.split(".")[0]
        .ljust(6, "0")[:6]
    )

    try:
        value = datetime.strptime(
            date + clean_time,
            "%Y%m%d%H%M%S",
        )

        return timezone.make_aware(
            value,
            timezone.get_current_timezone(),
        )

    except ValueError:
        return None


def fetch_study_snapshot(
    orthanc_study_id,
):
    study_url = (
        _base_url()
        + "/studies/"
        + quote(
            str(orthanc_study_id),
            safe="",
        )
    )

    study = _json_request(
        study_url
    )

    tags = (
        study.get("MainDicomTags")
        or {}
    )

    patient_tags = (
        study.get(
            "PatientMainDicomTags"
        )
        or {}
    )

    series_rows = []

    for orthanc_series_id in (
        study.get("Series") or []
    ):
        series_url = (
            _base_url()
            + "/series/"
            + quote(
                str(orthanc_series_id),
                safe="",
            )
        )

        series = _json_request(
            series_url
        )

        stags = (
            series.get("MainDicomTags")
            or {}
        )

        instances = (
            series.get("Instances")
            or []
        )

        instance_count = len(
            instances
        )

        modality = str(
            stags.get("Modality")
            or ""
        )

        is_complete = (
            instance_count > 0
        )

        series_rows.append({
            "orthanc_series_id":
                str(orthanc_series_id),

            "series_instance_uid":
                str(
                    stags.get(
                        "SeriesInstanceUID"
                    )
                    or ""
                ),

            "series_number":
                _int(
                    stags.get(
                        "SeriesNumber"
                    )
                ),

            "modality":
                modality,

            "series_description":
                str(
                    stags.get(
                        "SeriesDescription"
                    )
                    or ""
                ),

            "protocol_name":
                str(
                    stags.get(
                        "ProtocolName"
                    )
                    or ""
                ),

            "instance_count":
                instance_count,

            # Orthanc 기본 Snapshot:
            # multi-frame 상세 metadata가 없으면
            # instance count를 frame_count 하한값으로 사용.
            "frame_count":
                instance_count,

            "rows":
                _int(
                    stags.get("Rows")
                ),

            "columns":
                _int(
                    stags.get("Columns")
                ),

            "slice_thickness":
                _decimal(
                    stags.get(
                        "SliceThickness"
                    )
                ),

            "is_complete":
                is_complete,

            "is_ai_eligible": (
                is_complete
                and modality
                in {"CT", "MR"}
            ),

            "ai_exclusion_reason": (
                ""
                if (
                    is_complete
                    and modality
                    in {"CT", "MR"}
                )
                else "SERIES_NOT_AI_ELIGIBLE"
            ),
        })

    return {
        "orthanc_study_id":
            str(orthanc_study_id),

        "study_instance_uid":
            str(
                tags.get(
                    "StudyInstanceUID"
                )
                or ""
            ),

        "accession_number":
            str(
                tags.get(
                    "AccessionNumber"
                )
                or ""
            ),

        "patient_no":
            str(
                patient_tags.get(
                    "PatientID"
                )
                or ""
            ),

        "study_datetime":
            _study_datetime(tags),

        "study_description":
            str(
                tags.get(
                    "StudyDescription"
                )
                or ""
            ),

        "series":
            series_rows,
    }


def qido_series(
    study_instance_uid,
    *,
    series_instance_uid=None,
    modality=None,
    offset=None,
    limit=None,
):
    query = {}

    if series_instance_uid:
        query[
            "SeriesInstanceUID"
        ] = series_instance_uid

    if modality:
        query["Modality"] = modality

    if offset is not None:
        query["offset"] = offset

    if limit is not None:
        query["limit"] = limit

    url = (
        _dicomweb_base_url()
        + "/studies/"
        + quote(
            study_instance_uid,
            safe="",
        )
        + "/series"
    )

    if query:
        url += "?" + urlencode(query)

    data = _json_request(
        url,
        accept="application/dicom+json",
    )

    if not isinstance(data, list):
        raise OrthancUnavailable(
            "QIDO response must be an array."
        )

    return data
