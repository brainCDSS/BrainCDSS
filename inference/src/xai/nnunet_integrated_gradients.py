"""Original-space Smooth Integrated Gradients for nnU-Net predictions."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from .integrated_gradients import IntegratedGradients3D
from .nnunet_gradcam import (
    _gaussian_importance_map,
    _global_normalize,
    _gradient_network,
    _match_nifti_axes,
    _pad_to_patch,
    _predicted_lesion_roi,
    _restore_original_space,
)


def generate_nnunet_integrated_gradients(predictor, input_paths: list[Path], reference_path: Path, output_path: Path, *, channel_index: int | None = None) -> dict:
    """Generate a full-volume Smooth Integrated Gradients NIfTI."""
    import nibabel as nib
    import torch

    preprocessor = predictor.configuration_manager.preprocessor_class(verbose=False)
    data, _, properties = preprocessor.run_case(
        [str(path) for path in input_paths], None, predictor.plans_manager,
        predictor.configuration_manager, predictor.dataset_json,
    )
    patch_size = tuple(int(value) for value in predictor.configuration_manager.patch_size)
    padded, crop = _pad_to_patch(np.asarray(data, dtype=np.float32), patch_size)
    tensor = torch.from_numpy(padded)
    predicted_roi = _predicted_lesion_roi(predictor, tensor)
    network = _gradient_network(predictor)
    slicers = predictor._internal_get_sliding_window_slicers(tensor.shape[1:])
    heatmap, patch_count, attributed_patch_count = _aggregate(
        network, tensor, slicers, predictor.device, predicted_roi,
        steps=int(os.getenv("XAI_IG_STEPS", "8")),
        smooth_samples=int(os.getenv("XAI_SMOOTHGRAD_SAMPLES", "4")),
        noise_std=float(os.getenv("XAI_SMOOTHGRAD_NOISE_STD", "0.05")),
        channel_index=channel_index,
    )
    reference = nib.load(str(reference_path))
    original = _restore_original_space(heatmap[crop], predictor, properties)
    original = _match_nifti_axes(original, tuple(reference.shape[:3]))
    if tuple(original.shape) != tuple(reference.shape[:3]):
        raise ValueError(f"Integrated Gradients shape {original.shape} does not match source shape {reference.shape[:3]}")
    original = _global_normalize(original)
    header = reference.header.copy()
    header.set_data_dtype(np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(original.astype(np.float32), reference.affine, header), str(output_path))
    return {
        "method": "CAPTUM_SMOOTH_INTEGRATED_GRADIENTS_3D",
        "target": "PREDICTED_LESION_ROI_MEAN_FOREGROUND_LOGIT",
        "patch_count": patch_count,
        "attributed_patch_count": attributed_patch_count,
        "skipped_background_patch_count": patch_count - attributed_patch_count,
        "roi_source": "NNUNET_PREDICTED_SEGMENTATION",
        "segmentation_decision": "LABEL_MANAGER_CONVERT_LOGITS_TO_SEGMENTATION",
        "aggregation": "GAUSSIAN_WEIGHTED_MEAN",
        "normalization": "GLOBAL_ABS_MIN_MAX_0_1",
        "ig_steps": int(os.getenv("XAI_IG_STEPS", "8")),
        "smoothgrad_samples": int(os.getenv("XAI_SMOOTHGRAD_SAMPLES", "4")),
        "input_channel": channel_index,
    }


def _aggregate(network, tensor, slicers, device, predicted_roi, *, steps, smooth_samples, noise_std, channel_index: int | None = None):
    import torch

    heatmap_sum = np.zeros(tuple(int(value) for value in tensor.shape[1:]), dtype=np.float32)
    weight_sum = np.zeros_like(heatmap_sum)
    explainer = IntegratedGradients3D(network)
    patch_count = attributed_patch_count = 0
    gaussian = None
    for slicer in slicers:
        patch_count += 1
        spatial_slices = slicer[1:]
        roi_mask = predicted_roi[spatial_slices]
        if not roi_mask.any():
            continue
        network.zero_grad(set_to_none=True)
        patch = tensor[slicer][None].to(device, memory_format=torch.contiguous_format)
        attribution = explainer.attribute(
            patch, roi_mask, steps, smooth_samples, noise_std,
            channel_index=channel_index,
        )[0, 0].cpu().numpy().astype(np.float32)
        if gaussian is None or gaussian.shape != attribution.shape:
            gaussian = _gaussian_importance_map(tuple(attribution.shape))
        heatmap_sum[spatial_slices] += attribution * gaussian
        weight_sum[spatial_slices] += gaussian
        attributed_patch_count += 1
    heatmap = np.zeros_like(heatmap_sum)
    np.divide(heatmap_sum, weight_sum, out=heatmap, where=weight_sum > 0)
    return heatmap, patch_count, attributed_patch_count
