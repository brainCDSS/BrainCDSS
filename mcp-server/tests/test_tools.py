"""Read-only schema, scope and mock backend test."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"src"))
from backend_client.mock import MockBackendClient
from schemas.tool_context import ToolContext,ToolRequest
from tools.registry import TOOLS,handle
def test_all_tools_are_read_only_getters(): assert len(TOOLS)==7 and all(x.startswith("get_") for x in TOOLS)
def test_mock_result():
    req=ToolRequest(context=ToolContext(actor_id="synthetic",actor_role="patient",patient_scope=["synthetic-patient"],trace_id="trace-test"),patient_id="synthetic-patient")
    assert handle("get_patient_summary",req,MockBackendClient()).data["is_mock"] is True
