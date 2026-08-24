"""Every read-only tool carries identity scope and audit context."""
from pydantic import BaseModel
class ToolContext(BaseModel):
    actor_id:str; actor_role:str; patient_scope:list[str]; trace_id:str
class ToolRequest(BaseModel): context:ToolContext; patient_id:str
class ToolResult(BaseModel): status:str="NOT_IMPLEMENTED"; is_mock:bool=True; data:dict={}
