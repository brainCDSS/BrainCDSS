# Orthanc foundation for the AI demo

The existing `orthancteam/orthanc` container remains the DICOM archive. It uses
the persistent `orthanc-data` volume, HTTP authentication, localhost-only host
ports, and the DICOMweb plugin. Backend and Celery containers reach it over the
Compose network at `http://orthanc:8042`.

Start only the imaging components with:

```bash
docker compose --profile imaging up -d orthanc ohif
```

Set `ORTHANC_USERNAME` and `ORTHANC_PASSWORD` in the local `.env` first. In a
deployed environment, store the password in Secret Manager.

`apps.imaging.services.OrthancClient` provides the boundary needed by the next
pipeline step:

- read Study and Series metadata;
- download a Series archive for DICOM-to-NIfTI conversion;
- upload generated DICOM SEG and DICOM SR instances.

The converter is intentionally separate. It will consume a downloaded Series
and the inference mask, generate SEG/SR files, upload both through this client,
then create `DicomObjectReference` rows and link them to `AIResultArtifact`.
