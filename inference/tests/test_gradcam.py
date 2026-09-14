import pytest


torch = pytest.importorskip("torch")
pytest.importorskip("captum")

from src.xai.gradcam import GradCam3D, find_last_conv3d
from src.xai.nnunet_gradcam import _gradient_network, _match_nifti_axes


class TinySegmentation3D(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.features = torch.nn.Sequential(
            torch.nn.Conv3d(1, 4, kernel_size=3, padding=1),
            torch.nn.ReLU(),
            torch.nn.Conv3d(4, 4, kernel_size=3, padding=1),
            torch.nn.ReLU(),
        )
        self.head = torch.nn.Conv3d(4, 2, kernel_size=1)

    def forward(self, value):
        return self.head(self.features(value))


def test_gradcam_overrides_outer_inference_mode():
    with torch.inference_mode():
        model = TinySegmentation3D()
        source = torch.randn(1, 1, 8, 9, 10)
        with torch.inference_mode(False):
            normal_model = TinySegmentation3D()
            normal_model.load_state_dict({name: value.detach().clone() for name, value in model.state_dict().items()})
        attribution = GradCam3D(normal_model).attribute(source)

    assert tuple(attribution.shape) == (1, 1, 8, 9, 10)
    assert torch.isfinite(attribution).all()
    assert float(attribution.min()) >= 0
    assert float(attribution.max()) <= 1


def test_target_layer_avoids_one_by_one_segmentation_head():
    model = TinySegmentation3D()
    assert find_last_conv3d(model) is model.features[2]


def test_mosec_inference_model_is_rematerialized_for_backward():
    with torch.inference_mode():
        inference_model = TinySegmentation3D()
        predictor = type("Predictor", (), {
            "network": inference_model,
            "list_of_parameters": [inference_model.state_dict()],
            "device": torch.device("cpu"),
        })()

    model = _gradient_network(predictor)
    assert all(not parameter.is_inference() for parameter in model.parameters())
    source = torch.randn(1, 1, 8, 9, 10)
    attribution = GradCam3D(model).attribute(source)
    assert tuple(attribution.shape) == (1, 1, 8, 9, 10)


def test_nnunet_zyx_volume_is_returned_in_nifti_xyz_order():
    volume = torch.arange(73 * 112 * 112).reshape(73, 112, 112).numpy()

    aligned = _match_nifti_axes(volume, (112, 112, 73))

    assert aligned.shape == (112, 112, 73)
    assert aligned[4, 3, 2] == volume[2, 3, 4]


def test_matching_nifti_shape_is_not_transposed():
    volume = torch.zeros(12, 13, 14).numpy()
    assert _match_nifti_axes(volume, (12, 13, 14)) is volume
