"""Correlation ID propagation without logging sensitive request content."""
import uuid
class CorrelationIdMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        trace_id=request.headers.get("X-Trace-ID") or str(uuid.uuid4()); request.trace_id=trace_id
        response=self.get_response(request); response["X-Trace-ID"]=trace_id; return response

