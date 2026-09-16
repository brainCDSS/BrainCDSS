from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..config import DISEASE_QUERIES
from ..models import DiseaseEvidence, EvidenceUpdateState
from .serializers import ClinicalEvidenceSerializer, EvidenceQuerySerializer


class ClinicalEvidenceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(parameters=[EvidenceQuerySerializer])
    def get(self, request):
        query = EvidenceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        requested = query.validated_data.get("disease")
        limit = query.validated_data["limit"]
        groups = []
        for disease in (requested,) if requested else DISEASE_QUERIES:
            state = EvidenceUpdateState.objects.filter(key=disease).first()
            selections = DiseaseEvidence.objects.filter(disease_type=disease, is_active=True).select_related("evidence").order_by("display_rank", "evidence__pmid")[:limit]
            items = []
            for selection in selections:
                item = ClinicalEvidenceSerializer(selection.evidence).data
                item["display_rank"] = selection.display_rank
                items.append(item)
            groups.append({"updated_at": state.last_success_at.isoformat() if state and state.last_success_at else None,
                           "disease": disease, "items": items})
        # No external network or generation on the request path.
        if requested:
            return Response(groups[0])
        times = [group["updated_at"] for group in groups if group["updated_at"]]
        return Response({"updated_at": max(times) if times else None, "disease": "all", "items": groups})
