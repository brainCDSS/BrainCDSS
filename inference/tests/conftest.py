"""Make the inference application package importable from the repository root."""

import sys
from pathlib import Path


INFERENCE_ROOT = Path(__file__).parents[1]
if str(INFERENCE_ROOT) not in sys.path:
    sys.path.insert(0, str(INFERENCE_ROOT))
