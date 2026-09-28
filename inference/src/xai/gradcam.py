"""Captum LayerGradCam for 3-D segmentation networks.

The returned tensor remains in the network-input coordinate system. The caller
must apply the same inverse nnU-Net preprocessing used for the segmentation
before exporting it as a NIfTI artifact.
"""

from __future__ import annotations

from typing import Any


def find_last_conv3d(network):
    """Return the deepest Conv3d layer without depending on network naming."""
    import torch

    layers = [
        module
        for module in network.modules()
        if isinstance(module, torch.nn.Conv3d)
        and tuple(module.kernel_size) != (1, 1, 1)
    ]

    if not layers:
        layers = [
            module
            for module in network.modules()
            if isinstance(module, torch.nn.Conv3d)
        ]

    if not layers:
        raise ValueError("the model does not contain a Conv3d layer")

    return layers[-1]


def _normalize_attribution(attribution):
    """Normalize each Grad-CAM sample independently to the 0..1 range.

    Very small raw Grad-CAM magnitudes are valid. Therefore we must not clamp
    the denominator to a fixed epsilon such as 1e-8, because doing so prevents
    values with a legitimate range below that threshold from being normalized.

    Constant maps have no relative attribution information and are returned
    as zeros.
    """
    import torch

    flat = attribution.flatten(1)

    minimum = flat.min(dim=1).values[:, None, None, None, None]
    maximum = flat.max(dim=1).values[:, None, None, None, None]

    value_range = maximum - minimum

    # Avoid division by zero only for truly constant maps.
    safe_range = torch.where(
        value_range > 0,
        value_range,
        torch.ones_like(value_range),
    )

    normalized = (attribution - minimum) / safe_range

    # A constant attribution volume contains no spatial importance information.
    normalized = torch.where(
        value_range > 0,
        normalized,
        torch.zeros_like(normalized),
    )

    return normalized.clamp(0.0, 1.0)


class _SegmentationScore:
    """Use predicted-lesion foreground logits as a scalar Grad-CAM target."""

    def __init__(self, network, foreground_class: int, roi_mask=None):
        self.network = network
        self.foreground_class = foreground_class
        self.roi_mask = roi_mask

    def __call__(self, inputs):
        import torch

        logits: Any = self.network(inputs)

        if isinstance(logits, (tuple, list)):
            logits = logits[0]

        if self.roi_mask is None:
            raise ValueError(
                "Grad-CAM requires a predicted lesion ROI; "
                "top-voxel fallback is not supported"
            )

        foreground_logits = (
            logits[:, 0]
            if logits.shape[1] == 1
            else logits[:, self.foreground_class]
        )
        mask = torch.as_tensor(
            self.roi_mask,
            device=foreground_logits.device,
            dtype=foreground_logits.dtype,
        )

        if mask.ndim == foreground_logits.ndim - 1:
            mask = mask.unsqueeze(0)
        elif mask.ndim != foreground_logits.ndim:
            raise ValueError(
                "ROI mask dimensions do not match the model output"
            )

        denominator = mask.flatten(1).sum(dim=1)
        if bool(torch.any(denominator <= 0)):
            raise ValueError("Grad-CAM ROI must contain a predicted lesion voxel")

        score = (
            (foreground_logits * mask)
            .flatten(1)
            .sum(dim=1)
            / denominator
        )

        return score[:, None]


class GradCam3D:
    """Generate a normalized 3-D LayerGradCam attribution volume."""

    def __init__(
        self,
        network,
        target_layer=None,
        foreground_class: int = 1,
    ):
        self.network = network
        self.target_layer = (
            target_layer
            or find_last_conv3d(network)
        )
        self.foreground_class = foreground_class

    def attribute(
        self,
        inputs,
        roi_mask=None,
        normalize: bool = True,
    ):
        import torch
        from captum.attr import LayerGradCam

        wrapped = _SegmentationScore(
            self.network,
            self.foreground_class,
            roi_mask,
        )

        was_training = self.network.training
        self.network.eval()

        try:
            # MOSEC / nnU-Net predictors can execute inside
            # torch.inference_mode(). enable_grad() alone does not override it.
            with torch.inference_mode(False), torch.enable_grad():
                tensor = (
                    inputs
                    .detach()
                    .clone()
                    .requires_grad_(True)
                )

                attribution = LayerGradCam(
                    wrapped,
                    self.target_layer,
                ).attribute(
                    tensor,
                    target=0,
                )

                # Keep only positive contribution to the foreground target.
                attribution = torch.relu(attribution)

                # LayerGradCam is generated at the target layer resolution.
                # Restore it to the network input spatial resolution.
                attribution = torch.nn.functional.interpolate(
                    attribution,
                    size=tensor.shape[2:],
                    mode="trilinear",
                    align_corners=False,
                )

                # Collapse target-layer channels into one heatmap.
                attribution = attribution.mean(
                    dim=1,
                    keepdim=True,
                )

                # Normalize relative importance to 0..1 even when the raw
                # attribution values are extremely small (for example 1e-9).
                if normalize:
                    attribution = _normalize_attribution(
                        attribution
                    )

                return attribution.detach()

        finally:
            self.network.train(was_training)
