"""Audit sink records outcome, duration and trace, never clinical payload."""
from typing import Protocol
class AuditSink(Protocol):
    def record(self,tool:str,success:bool,duration_ms:int,trace_id:str)->None: ...
