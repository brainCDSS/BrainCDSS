from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.imaging.models import ImagingStudy, NiftiArtifact
from apps.imaging.services.nifti import open_gcs_artifact, study_input_bundles


CLINICAL_ROLES = {"NEUROLOGIST", "NEUROSURGEON", "RADIOLOGY"}


class ClinicalNiftiView(APIView):
    permission_classes = [IsAuthenticated]

    def check_role(self, request):
        role = getattr(getattr(request.user, "role", None), "code", None)
        if role not in CLINICAL_ROLES:
            raise Http404


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
