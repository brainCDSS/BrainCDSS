"""Autodiscovered AI analysis tasks."""

from .inference import run_analysis_inference
from .mock_inference import run_mock_analysis_inference

__all__ = ["run_analysis_inference", "run_mock_analysis_inference"]
