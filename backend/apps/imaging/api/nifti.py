from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_analysis.models import AIAnalysis
from apps.imaging.models import ImagingStudy, NiftiArtifact, SeriesReference
from apps.imaging.services.nifti import open_gcs_artifact, study_input_bundles


CLINICAL_ROLES = {"NEUROLOGIST", "NEUROSURGEON", "RADIOLOGY"}


class ClinicalNiftiView(APIView):
    permission_classes = [IsAuthenticated]

    def check_role(self, request):
        role = getattr(getattr(request.user, "role", None), "code", None)
        if role not in CLINICAL_ROLES:
            raise Http404


def _study_payload(study):
    series = list(SeriesReference.objects.filter(study=study).order_by("series_number"))
    latest = AIAnalysis.objects.filter(study=study).order_by("-requested_at").first()
    roles = set(NiftiArtifact.objects.filter(series__study=study).values_list("role", flat=True))
    return {
        "study_id": str(study.id),
        "study_instance_uid": study.study_instance_uid,
        "accession_number": study.accession_number,
        "study_datetime": study.study_datetime,
        "modalities": study.modalities or sorted({item.modality for item in series}),
        "scan_type": "MRA" if "MRA" in roles else None,
        "study_description": study.study_description,
        "status": study.status,
        "series_count": len(series),
        "instance_count": sum(item.instance_count for item in series),
        "patient": None if study.patient is None else {
            "patient_id": str(study.patient_id),
            "patient_no": study.patient.patient_no,
            "name": study.patient.name,
            "birth_date": study.patient.birth_date,
            "estimated_age": study.patient.estimated_age,
            "sex": study.patient.sex,
        },
        "latest_analysis": None if latest is None else {
            "analysis_id": str(latest.id), "status": latest.status,
        },
        "current_report": None,
        "critical_finding": False,
    }


def _series_payload(item):
    return {
        "series_id": str(item.id),
        "series_instance_uid": item.series_instance_uid,
        "series_number": item.series_number,
        "modality": item.modality,
        "series_description": item.series_description,
        "protocol_name": item.protocol_name,
        "instance_count": item.instance_count,
        "frame_count": item.frame_count,
        "rows": item.rows,
        "columns": item.columns,
        "slice_thickness": item.slice_thickness,
        "is_complete": item.is_complete,
        "is_ai_eligible": item.is_ai_eligible,
        "ai_exclusion_reason": item.ai_exclusion_reason,
    }


class ImagingStudyCollectionView(ClinicalNiftiView):
    def get(self, request):
        self.check_role(request)
        studies = ImagingStudy.objects.select_related("patient").order_by("-study_datetime", "-created_at")
        patient_id = request.query_params.get("patient_id")
        if patient_id:
            studies = studies.filter(patient_id=patient_id)
        rows = [_study_payload(study) for study in studies]
        return Response({"count": len(rows), "next": None, "previous": None, "results": rows})


class ImagingStudyDetailView(ClinicalNiftiView):
    def get(self, request, study_id):
        self.check_role(request)
        study = ImagingStudy.objects.select_related("patient").filter(pk=study_id).first()
        if study is None:
            raise Http404
        payload = _study_payload(study)
        payload["series"] = [
            _series_payload(item)
            for item in SeriesReference.objects.filter(study=study).order_by("series_number")
        ]
        return Response(payload)


class ImagingStudySeriesView(ClinicalNiftiView):
    def get(self, request, study_id):
        self.check_role(request)
        if not ImagingStudy.objects.filter(pk=study_id).exists():
            raise Http404
        return Response({
            "study_id": str(study_id),
            "series": [
                _series_payload(item)
                for item in SeriesReference.objects.filter(study_id=study_id).order_by("series_number")
            ],
        })


class StudyAIInputsView(ClinicalNiftiView):
    def get(self, request, study_id):
        self.check_role(request)
        study = ImagingStudy.objects.filter(pk=study_id, status="AVAILABLE").first()
        if study is None:
            raise Http404
        return Response({"study_id": str(study.id), "bundles": study_input_bundles(study)})


class NiftiArtifactContentView(ClinicalNiftiView):
    def get(self, request, artifact_id):
        self.check_role(request)
        artifact = NiftiArtifact.objects.filter(pk=artifact_id).first()
        if artifact is None:
            raise Http404
        return open_gcs_artifact(artifact)
