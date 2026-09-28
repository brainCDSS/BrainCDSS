"""Generate an original-space Grad-CAM NIfTI from an initialized nnU-Net predictor."""

from __future__ import annotations

from pathlib import Path
from itertools import permutations

import numpy as np

from .gradcam import GradCam3D, find_last_conv3d


def generate_nnunet_gradcam(predictor, input_paths: list[Path], reference_path: Path, output_path: Path) -> dict:
    """Run full sliding-window Grad-CAM and reverse nnU-Net preprocessing."""
    import nibabel as nib
    import torch

    preprocessor = predictor.configuration_manager.preprocessor_class(verbose=False)
    data, _, properties = preprocessor.run_case(
        [str(path) for path in input_paths],
        None,
        predictor.plans_manager,
        predictor.configuration_manager,
        predictor.dataset_json,
    )
    data = np.asarray(data, dtype=np.float32)
    patch_size = tuple(int(value) for value in predictor.configuration_manager.patch_size)
    padded, crop = _pad_to_patch(data, patch_size)
    tensor = torch.from_numpy(padded)
    network = _gradient_network(predictor)
    network.eval()

    slicers = predictor._internal_get_sliding_window_slicers(tensor.shape[1:])
    predicted_roi = _predicted_lesion_roi(predictor, tensor)
    target_layer = find_last_conv3d(network)
    heatmap, patch_count, attributed_patch_count = _aggregate_sliding_window_gradcam(
        network,
        tensor,
        slicers,
        predictor.device,
        GradCam3D(network, target_layer=target_layer),
        predicted_roi,
    )
    heatmap = heatmap[crop]
    reference = nib.load(str(reference_path))
    original_space = _restore_original_space(heatmap, predictor, properties)
    original_space = _match_nifti_axes(original_space, tuple(reference.shape[:3]))
    if tuple(original_space.shape) != tuple(reference.shape[:3]):
        raise ValueError(
            f"Grad-CAM shape {original_space.shape} does not match source shape {reference.shape[:3]}"
        )
    original_space = _global_normalize(original_space)
    header = reference.header.copy()
    header.set_data_dtype(np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(original_space.astype(np.float32), reference.affine, header), str(output_path))
    return {
        "method": "CAPTUM_LAYER_GRAD_CAM_3D",
        "target": "PREDICTED_LESION_ROI_MEAN_FOREGROUND_LOGIT",
        "target_layer": _module_name(network, target_layer),
        "patch_count": patch_count,
        "attributed_patch_count": attributed_patch_count,
        "skipped_background_patch_count": patch_count - attributed_patch_count,
        "roi_source": "NNUNET_PREDICTED_SEGMENTATION",
        "segmentation_decision": "LABEL_MANAGER_CONVERT_LOGITS_TO_SEGMENTATION",
        "aggregation": "GAUSSIAN_WEIGHTED_MEAN",
        "normalization": "GLOBAL_RELU_MIN_MAX_0_1",
    }


def _gaussian_importance_map(patch_size: tuple[int, ...], sigma_scale: float = 1 / 8) -> np.ndarray:
    """Create a strictly positive, center-normalized 3-D Gaussian map."""
    axes = []
    for size in patch_size:
        coordinates = np.arange(size, dtype=np.float32) - (size - 1) / 2
        sigma = max(float(size) * sigma_scale, np.finfo(np.float32).eps)
        axes.append(np.exp(-0.5 * (coordinates / sigma) ** 2))
    gaussian = axes[0][:, None, None] * axes[1][None, :, None] * axes[2][None, None, :]
    gaussian /= float(gaussian.max())
    return np.maximum(gaussian, np.finfo(np.float32).tiny).astype(np.float32)


def _predicted_lesion_roi(predictor, tensor) -> np.ndarray:
    """Re-use nnU-Net's production segmentation decision for the XAI ROI."""
    import torch

    with torch.inference_mode():
        predicted_logits = predictor.predict_logits_from_preprocessed_data(tensor)
        segmentation = predictor.label_manager.convert_logits_to_segmentation(
            predicted_logits,
        )
    if isinstance(segmentation, torch.Tensor):
        segmentation = segmentation.cpu().numpy()
    return np.isin(
        np.asarray(segmentation),
        predictor.label_manager.foreground_labels,
    )


def _aggregate_sliding_window_gradcam(
    network,
    tensor,
    slicers,
    device,
    gradcam,
    predicted_roi,
):
    import torch

    spatial_shape = tuple(int(value) for value in tensor.shape[1:])
    heatmap_sum = np.zeros(spatial_shape, dtype=np.float32)
    weight_sum = np.zeros(spatial_shape, dtype=np.float32)
    patch_count = 0
    attributed_patch_count = 0
    gaussian = None
    for slicer in slicers:
        patch_count += 1
        spatial_slices = slicer[1:]
        roi_mask = predicted_roi[spatial_slices]
        if not roi_mask.any():
            continue

        network.zero_grad(set_to_none=True)
        patch = tensor[slicer][None].to(device, memory_format=torch.contiguous_format)
        attribution = gradcam.attribute(
            patch,
            roi_mask=roi_mask,
            normalize=False,
        )[0, 0].cpu().numpy().astype(np.float32)
        if gaussian is None or gaussian.shape != attribution.shape:
            gaussian = _gaussian_importance_map(tuple(attribution.shape))
        heatmap_sum[spatial_slices] += attribution * gaussian
        weight_sum[spatial_slices] += gaussian
        attributed_patch_count += 1
    if patch_count == 0:
        raise ValueError("nnU-Net returned no sliding-window slicers")
    heatmap = np.zeros_like(heatmap_sum)
    np.divide(heatmap_sum, weight_sum, out=heatmap, where=weight_sum > 0)
    return heatmap, patch_count, attributed_patch_count


def _global_normalize(volume: np.ndarray) -> np.ndarray:
    """Apply ReLU and one global min-max normalization without fixed epsilon."""
    positive = np.maximum(np.asarray(volume, dtype=np.float32), 0)
    minimum = float(positive.min())
    maximum = float(positive.max())
    value_range = maximum - minimum
    if value_range <= 0:
        return np.zeros_like(positive, dtype=np.float32)
    return ((positive - minimum) / value_range).astype(np.float32)


def _pad_to_patch(data: np.ndarray, patch_size: tuple[int, ...]):
    padding = [(0, 0)]
    crop = []
    for current, target in zip(data.shape[1:], patch_size):
        total = max(0, target - current)
        before = total // 2
        after = total - before
        padding.append((before, after))
        crop.append(slice(before, before + current))
    return np.pad(data, padding, mode="constant"), tuple(crop)


def _restore_original_space(heatmap: np.ndarray, predictor, properties: dict) -> np.ndarray:
    import torch

    plans = predictor.plans_manager
    configuration = predictor.configuration_manager
    spacing_transposed = [properties["spacing"][i] for i in plans.transpose_forward]
    current_spacing = (
        configuration.spacing
        if len(configuration.spacing) == len(properties["shape_after_cropping_and_before_resampling"])
        else [spacing_transposed[0], *configuration.spacing]
    )
    restored = configuration.resampling_fn_probabilities(
        torch.from_numpy(heatmap[None]),
        properties["shape_after_cropping_and_before_resampling"],
        current_spacing,
        spacing_transposed,
    )
    if isinstance(restored, torch.Tensor):
        restored = restored.cpu().numpy()
    restored = np.asarray(restored[0], dtype=np.float32)
    canvas = np.zeros(properties["shape_before_cropping"], dtype=np.float32)
    bbox = properties["bbox_used_for_cropping"]
    canvas[tuple(slice(int(bounds[0]), int(bounds[1])) for bounds in bbox)] = restored
    return canvas.transpose(plans.transpose_backward)


def _match_nifti_axes(volume: np.ndarray, reference_shape: tuple[int, ...]) -> np.ndarray:
    """Return nnU-Net spatial data in the reference NIfTI voxel-axis order.

    nnU-Net readers commonly expose voxel arrays as Z,Y,X while nibabel exposes
    the same NIfTI as X,Y,Z. Some plans transpose those axes during preprocessing,
    so first keep an already matching array, then prefer the explicit ZYX->XYZ
    reversal. A remaining shape permutation is accepted only when it is unique;
    ambiguous geometry is rejected instead of publishing a misregistered XAI map.
    """
    if tuple(volume.shape) == reference_shape:
        return volume

    reversed_axes = tuple(reversed(range(volume.ndim)))
    reversed_volume = volume.transpose(reversed_axes)
    if tuple(reversed_volume.shape) == reference_shape:
        return reversed_volume

    candidates = [
        axes
        for axes in permutations(range(volume.ndim))
        if tuple(volume.shape[index] for index in axes) == reference_shape
    ]
    if len(candidates) == 1:
        return volume.transpose(candidates[0])
    raise ValueError(
        f"Cannot unambiguously align Grad-CAM shape {volume.shape} "
        f"to source shape {reference_shape}"
    )


def _module_name(network, target) -> str:
    for name, module in network.named_modules():
        if module is target:
            return name
    return target.__class__.__name__


def _gradient_network(predictor):
    """Materialize a grad-capable copy of a model created by a MOSEC worker.

    MOSEC may construct the nnU-Net predictor while torch.inference_mode is
    active. Such parameters cannot participate in Captum backward even after
    enable_grad. Deep-copying and reloading cloned weights with inference mode
    explicitly disabled creates ordinary tensors without mutating the cached
    production predictor.
    """
    import copy
    import torch

    source = predictor.network
    if hasattr(source, "_orig_mod"):
        source = source._orig_mod
    with torch.inference_mode(False):
        network = copy.deepcopy(source)
        state = {
            name: value.detach().clone()
            for name, value in predictor.list_of_parameters[0].items()
        }
        network.load_state_dict(state)
        network = network.to(predictor.device)
    network.eval()
    return network
