"""Model bundle loader protocol."""

from typing import Protocol


class ModelBundleLoader(Protocol):
    def prepare(self, selector, analysis_type):
        """Return a verified manifest, local bundle directory, and manifest URI."""
