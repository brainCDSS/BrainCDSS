"""Django internal API boundary; implementations must never query PostgreSQL."""
from abc import ABC, abstractmethod
class BackendClient(ABC):
    @abstractmethod
    def get(self,path:str,trace_id:str)->dict: ...
