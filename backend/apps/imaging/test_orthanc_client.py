import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.imaging.services.orthanc import OrthancClient, OrthancError


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class OrthancClientTests(SimpleTestCase):
    def setUp(self):
        self.client = OrthancClient(
            base_url="http://orthanc:8042", username="brainon", password="secret"
        )

    @patch("apps.imaging.services.orthanc.urlopen")
    def test_downloads_series_archive_with_server_side_credentials(self, send):
        send.return_value = _Response(b"PK synthetic zip")
        with tempfile.TemporaryDirectory() as directory:
            target = self.client.download_series_archive("series-id", Path(directory) / "series.zip")
            self.assertEqual(target.read_bytes(), b"PK synthetic zip")
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, "http://orthanc:8042/series/series-id/archive")
        self.assertTrue(request.headers["Authorization"].startswith("Basic "))

    @patch("apps.imaging.services.orthanc.urlopen")
    def test_uploads_generated_dicom_instance(self, send):
        send.return_value = _Response(json.dumps({
            "ID": "instance-id", "ParentSeries": "series-id",
            "ParentStudy": "study-id", "Status": "Success",
        }).encode())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result-seg.dcm"
            path.write_bytes(b"synthetic dicom")
            uploaded = self.client.upload_instance(path)
        self.assertEqual(uploaded.orthanc_instance_id, "instance-id")
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, "http://orthanc:8042/instances")
        self.assertEqual(request.headers["Content-type"], "application/dicom")

    def test_rejects_path_injection_in_resource_id(self):
        with self.assertRaises(OrthancError) as raised:
            self.client.get_series("../system")
        self.assertEqual(raised.exception.code, "ORTHANC_INVALID_ID")
