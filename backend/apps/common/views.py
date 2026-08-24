"""Non-sensitive liveness endpoint."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request): return Response({"status":"ok","service":"backend","trace_id":getattr(request,"trace_id","")})

