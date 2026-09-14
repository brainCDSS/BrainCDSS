import numpy as np
import pytest


torch = pytest.importorskip("torch")
pytest.importorskip("captum")

from src.xai.gradcam import (
    GradCam3D,
    _normalize_attribution,
    find_last_conv3d,
)
from src.xai.nnunet_gradcam import (
    _aggregate_sliding_window_gradcam,
    _gaussian_importance_map,
    _global_normalize,
    _gradient_network,
    _match_nifti_axes,
    _predicted_lesion_roi,
)


def test_gradcam_tiny_values_are_normalized_to_zero_one():
    """Very small but non-constant Grad-CAM values must still map to 0..1."""

    attribution = torch.tensor(
        [[[[[
            0.0,
            1e-10,
            8e-10,
            2.7e-9,
            9.7e-9,
        ]]]]],
        dtype=torch.float32,
    )

    normalized = _normalize_attribution(attribution)

    assert float(normalized.min()) == 0.0
    assert float(normalized.max()) == pytest.approx(1.0, abs=1e-6)
    assert torch.isfinite(normalized).all()


def test_gradcam_constant_values_become_zero():
    """A constant attribution map has no relative spatial importance."""

    attribution = torch.full(
        (1, 1, 2, 3, 4),
        1e-10,
        dtype=torch.float32,
    )

    normalized = _normalize_attribution(attribution)

    assert torch.isfinite(normalized).all()
    assert float(normalized.min()) == 0.0
    assert float(normalized.max()) == 0.0
    assert torch.count_nonzero(normalized) == 0


class TinySegmentation3D(torch.nn.Module):
    def __init__(self):
        super().__init__()

        self.features = torch.nn.Sequential(
            torch.nn.Conv3d(
                1,
                4,
                kernel_size=3,
                padding=1,
            ),
            torch.nn.ReLU(),
            torch.nn.Conv3d(
                4,
                4,
                kernel_size=3,
                padding=1,
            ),
            torch.nn.ReLU(),
        )

        self.head = torch.nn.Conv3d(
            4,
            2,
            kernel_size=1,
        )

    def forward(self, value):
        return self.head(
            self.features(value)
        )


def test_gradcam_overrides_outer_inference_mode():
    with torch.inference_mode():
        model = TinySegmentation3D()

        source = torch.randn(
            1,
            1,
            8,
            9,
            10,
        )

        with torch.inference_mode(False):
            normal_model = TinySegmentation3D()

            normal_model.load_state_dict(
                {
                    name: value.detach().clone()
                    for name, value
                    in model.state_dict().items()
                }
            )

        attribution = GradCam3D(
            normal_model
        ).attribute(
            source,
            roi_mask=torch.ones_like(source[:, 0], dtype=torch.bool),
        )

    assert tuple(attribution.shape) == (
        1,
        1,
        8,
        9,
        10,
    )

    assert torch.isfinite(
        attribution
    ).all()

    assert float(
        attribution.min()
    ) >= 0

    assert float(
        attribution.max()
    ) <= 1


def test_gradcam_normalize_false_returns_raw_positive_attribution():
    torch.manual_seed(7)
    model = TinySegmentation3D()
    source = torch.randn(1, 1, 8, 9, 10)
    gradcam = GradCam3D(model)

    roi = torch.ones_like(source[:, 0], dtype=torch.bool)
    raw = gradcam.attribute(source, roi_mask=roi, normalize=False)
    normalized = gradcam.attribute(source, roi_mask=roi, normalize=True)

    assert raw.shape == normalized.shape
    assert torch.isfinite(raw).all()
    assert float(raw.min()) >= 0
    assert float(normalized.max()) == pytest.approx(1.0, abs=1e-6)
    assert not torch.allclose(raw, normalized)


def test_gradcam_requires_a_predicted_lesion_roi():
    model = TinySegmentation3D()
    source = torch.randn(1, 1, 8, 9, 10)

    with pytest.raises(ValueError, match="predicted lesion ROI"):
        GradCam3D(model).attribute(source, normalize=False)


def test_gradcam_target_is_mean_foreground_logit_within_roi():
    class FixedLogits(torch.nn.Module):
        def forward(self, value):
            foreground = value[:, :1]
            return torch.cat((torch.zeros_like(foreground), foreground), dim=1)

    model = FixedLogits()
    source = torch.tensor([[[[[1.0, 4.0], [2.0, 8.0]]]]])
    roi = torch.tensor([[[[False, True], [False, True]]]]).numpy()

    from src.xai.gradcam import _SegmentationScore

    score = _SegmentationScore(model, foreground_class=1, roi_mask=roi)(source)

    assert float(score[0, 0]) == pytest.approx(6.0)


def test_global_volume_normalization_handles_tiny_nonconstant_range():
    volume = torch.tensor([0.0, 1e-10, 9e-10], dtype=torch.float32).numpy()
    normalized = _global_normalize(volume)

    assert float(normalized.min()) == 0.0
    assert float(normalized.max()) == pytest.approx(1.0, abs=1e-6)


def test_gaussian_importance_map_has_positive_edges_and_unit_center():
    gaussian = _gaussian_importance_map((5, 7, 9))

    assert gaussian.shape == (5, 7, 9)
    assert float(gaussian.min()) > 0
    assert float(gaussian[2, 3, 4]) == pytest.approx(1.0)


def test_overlapping_patches_are_aggregated_with_gaussian_weighted_mean():
    class FakeGradCam:
        def __init__(self):
            self.values = iter((2.0, 6.0))

        def attribute(self, patch, roi_mask=None, normalize=True):
            assert normalize is False
            assert roi_mask is not None
            return torch.full((1, 1, *patch.shape[2:]), next(self.values))

    model = TinySegmentation3D()
    tensor = torch.zeros(1, 3, 3, 5)
    slicers = [
        (slice(None), slice(0, 3), slice(0, 3), slice(0, 3)),
        (slice(None), slice(0, 3), slice(0, 3), slice(2, 5)),
    ]
    predicted_roi = torch.ones(3, 3, 5, dtype=torch.bool).numpy()

    heatmap, patch_count, attributed_patch_count = _aggregate_sliding_window_gradcam(
        model, tensor, slicers, torch.device("cpu"), FakeGradCam(), predicted_roi
    )
    gaussian = _gaussian_importance_map((3, 3, 3))
    expected_overlap = (2.0 * gaussian[1, 1, 2] + 6.0 * gaussian[1, 1, 0]) / (
        gaussian[1, 1, 2] + gaussian[1, 1, 0]
    )

    assert patch_count == 2
    assert attributed_patch_count == 2
    assert heatmap[1, 1, 0] == pytest.approx(2.0)
    assert heatmap[1, 1, 4] == pytest.approx(6.0)
    assert heatmap[1, 1, 2] == pytest.approx(expected_overlap)


def test_background_only_patches_are_skipped_without_backward():
    class FakeGradCam:
        def __init__(self):
            self.calls = 0

        def attribute(self, patch, roi_mask=None, normalize=True):
            self.calls += 1
            assert roi_mask.any()
            return torch.ones((1, 1, *patch.shape[2:]))

    model = TinySegmentation3D()
    tensor = torch.zeros(1, 3, 3, 5)
    slicers = [
        (slice(None), slice(0, 3), slice(0, 3), slice(0, 3)),
        (slice(None), slice(0, 3), slice(0, 3), slice(2, 5)),
    ]
    predicted_roi = np.zeros((3, 3, 5), dtype=bool)
    predicted_roi[1, 1, 4] = True
    gradcam = FakeGradCam()

    heatmap, patch_count, attributed_patch_count = _aggregate_sliding_window_gradcam(
        model, tensor, slicers, torch.device("cpu"), gradcam, predicted_roi
    )

    assert patch_count == 2
    assert attributed_patch_count == 1
    assert gradcam.calls == 1
    assert np.count_nonzero(heatmap[:, :, :2]) == 0


def test_negative_prediction_creates_an_all_zero_gradcam_volume():
    model = TinySegmentation3D()
    tensor = torch.zeros(1, 3, 3, 3)
    slicers = [(slice(None), slice(0, 3), slice(0, 3), slice(0, 3))]

    heatmap, patch_count, attributed_patch_count = _aggregate_sliding_window_gradcam(
        model,
        tensor,
        slicers,
        torch.device("cpu"),
        object(),
        np.zeros((3, 3, 3), dtype=bool),
    )

    assert patch_count == 1
    assert attributed_patch_count == 0
    assert np.count_nonzero(heatmap) == 0


def test_predicted_roi_uses_nnunet_label_manager_decision():
    class LabelManager:
        foreground_labels = [1]

        def convert_logits_to_segmentation(self, logits):
            return logits.argmax(0)

    class Predictor:
        label_manager = LabelManager()

        def predict_logits_from_preprocessed_data(self, tensor):
            return torch.tensor(
                [
                    [[[3.0, 1.0]]],
                    [[[1.0, 4.0]]],
                ]
            )

    roi = _predicted_lesion_roi(Predictor(), torch.zeros(1, 1, 1, 2))

    assert roi.tolist() == [[[False, True]]]


def test_target_layer_avoids_one_by_one_segmentation_head():
    model = TinySegmentation3D()

    assert (
        find_last_conv3d(model)
        is model.features[2]
    )


def test_mosec_inference_model_is_rematerialized_for_backward():
    with torch.inference_mode():
        inference_model = TinySegmentation3D()

        predictor = type(
            "Predictor",
            (),
            {
                "network": inference_model,
                "list_of_parameters": [
                    inference_model.state_dict()
                ],
                "device": torch.device("cpu"),
            },
        )()

    model = _gradient_network(
        predictor
    )

    assert all(
        not parameter.is_inference()
        for parameter in model.parameters()
    )

    source = torch.randn(
        1,
        1,
        8,
        9,
        10,
    )

    attribution = GradCam3D(
        model
    ).attribute(
        source,
        roi_mask=torch.ones_like(source[:, 0], dtype=torch.bool),
    )

    assert tuple(
        attribution.shape
    ) == (
        1,
        1,
        8,
        9,
        10,
    )


def test_nnunet_zyx_volume_is_returned_in_nifti_xyz_order():
    volume = (
        torch.arange(
            73 * 112 * 112
        )
        .reshape(
            73,
            112,
            112,
        )
        .numpy()
    )

    aligned = _match_nifti_axes(
        volume,
        (
            112,
            112,
            73,
        ),
    )

    assert aligned.shape == (
        112,
        112,
        73,
    )

    assert (
        aligned[4, 3, 2]
        == volume[2, 3, 4]
    )


def test_matching_nifti_shape_is_not_transposed():
    volume = torch.zeros(
        12,
        13,
        14,
    ).numpy()

    assert (
        _match_nifti_axes(
            volume,
            (
                12,
                13,
                14,
            ),
        )
        is volume
    )
