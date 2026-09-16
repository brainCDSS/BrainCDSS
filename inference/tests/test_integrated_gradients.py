import numpy as np
import pytest


torch = pytest.importorskip("torch")
pytest.importorskip("captum")

from src.xai.integrated_gradients import IntegratedGradients3D
from src.xai.nnunet_integrated_gradients import _aggregate


class TinySegmentation3D(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.features = torch.nn.Sequential(
            torch.nn.Conv3d(1, 4, 3, padding=1), torch.nn.ReLU(),
        )
        self.head = torch.nn.Conv3d(4, 2, 1)

    def forward(self, value):
        return self.head(self.features(value))


def test_smooth_integrated_gradients_returns_input_space_heatmap():
    model = TinySegmentation3D()
    image = torch.randn(1, 1, 5, 6, 7)
    roi = np.zeros((5, 6, 7), dtype=bool)
    roi[2, 3, 4] = True

    heatmap = IntegratedGradients3D(model).attribute(image, roi, steps=4, smooth_samples=2)

    assert heatmap.shape == (1, 1, 5, 6, 7)
    assert torch.isfinite(heatmap).all()
    assert float(heatmap.min()) >= 0


def test_negative_prediction_skips_all_integrated_gradients_calls():
    model = TinySegmentation3D()
    tensor = torch.zeros(1, 3, 3, 3)
    slicers = [(slice(None), slice(0, 3), slice(0, 3), slice(0, 3))]

    heatmap, patch_count, attributed_patch_count = _aggregate(
        model, tensor, slicers, torch.device("cpu"), np.zeros((3, 3, 3), dtype=bool),
        steps=4, smooth_samples=2, noise_std=0.05,
    )

    assert patch_count == 1
    assert attributed_patch_count == 0
    assert np.count_nonzero(heatmap) == 0
