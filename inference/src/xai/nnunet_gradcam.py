"""Generate an original-space Grad-CAM NIfTI from an initialized nnU-Net predictor."""

from __future__ import annotations

from pathlib import Path
from itertools import permutations

import numpy as np

from .gradcam import GradCam3D, find_last_conv3d


def generate_nnunet_gradcam(predictor, input_paths: list[Path], reference_path: Path, output_path: Path) -> dict:
    """Run patch-level Grad-CAM and reverse nnU-Net spatial preprocessing.

    A representative patch is selected using the highest foreground top-voxel
    probability. This avoids labeling the segmentation mask itself as XAI and
    keeps the attribution tied to an actual differentiable network forward pass.
    """
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
    selected, selected_score = _select_foreground_patch(network, tensor, slicers, predictor.device)
    patch = tensor[selected][None].to(predictor.device, memory_format=torch.contiguous_format)
    target_layer = find_last_conv3d(network)
    attribution = GradCam3D(network, target_layer=target_layer).attribute(patch)[0, 0].cpu().numpy()

    heatmap = np.zeros(tensor.shape[1:], dtype=np.float32)
    spatial_slices = selected[1:]
    heatmap[spatial_slices] = np.maximum(heatmap[spatial_slices], attribution)
    heatmap = heatmap[crop]
    reference = nib.load(str(reference_path))
    original_space = _restore_original_space(heatmap, predictor, properties)
    original_space = _match_nifti_axes(original_space, tuple(reference.shape[:3]))
    if tuple(original_space.shape) != tuple(reference.shape[:3]):
        raise ValueError(
            f"Grad-CAM shape {original_space.shape} does not match source shape {reference.shape[:3]}"
        )
    header = reference.header.copy()
    header.set_data_dtype(np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(original_space.astype(np.float32), reference.affine, header), str(output_path))
    return {
        "method": "CAPTUM_LAYER_GRAD_CAM_3D",
        "target": "FOREGROUND_TOP_0_1_PERCENT_MEAN",
        "target_layer": _module_name(network, target_layer),
        "representative_patch_score": float(selected_score),
        "normalization": "RELU_MIN_MAX_0_1",
    }


def _select_foreground_patch(network, tensor, slicers, device):
    import torch

    best_slice = slicers[0]
    best_score = float("-inf")
    with torch.inference_mode():
        for slicer in slicers:
            output = network(tensor[slicer][None].to(device, memory_format=torch.contiguous_format))
            if isinstance(output, (tuple, list)):
                output = output[0]
            foreground = torch.sigmoid(output[:, 0]) if output.shape[1] == 1 else torch.softmax(output, dim=1)[:, 1]
            flat = foreground.flatten()
            top_count = max(1, int(flat.numel() * 0.001))
            score = float(flat.topk(top_count).values.mean().item())
            if score > best_score:
                best_slice, best_score = slicer, score
    return best_slice, best_score


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
