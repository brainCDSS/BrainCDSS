"""GCS/MLflow model bundle loader interface; no weights are stored here."""
from abc import ABC, abstractmethod
class ModelBundleLoader(ABC):
    @abstractmethod
    def load(self, artifact_uri: str, checksum: str) -> object: """Verify and load an approved bundle."""
