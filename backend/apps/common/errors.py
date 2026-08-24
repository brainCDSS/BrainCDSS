"""Maps DRF errors to the common contract envelope."""
from rest_framework.views import exception_handler
def api_exception_handler(exc, context):
    response=exception_handler(exc,context)
    if response is None: return None
    request=context.get("request"); trace_id=getattr(request,"trace_id","")
    response.data={"error":{"code":getattr(exc,"default_code","API_ERROR"),"message":"요청을 처리하지 못했습니다.","details":response.data},"trace_id":trace_id}; return response

