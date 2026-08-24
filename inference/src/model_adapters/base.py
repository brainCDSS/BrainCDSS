"""Stable interface implemented by each deployable disease model adapter."""
from abc import ABC, abstractmethod
class ModelAdapter(ABC):
    @abstractmethod
    def predict(self, prepared_input: object) -> object: """Return raw output; clinical validation is downstream."""
