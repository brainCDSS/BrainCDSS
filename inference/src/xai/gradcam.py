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
        if isinstance(module, torch.nn.Conv3d) and tuple(module.kernel_size) != (1, 1, 1)
    ]
    if not layers:
        layers = [module for module in network.modules() if isinstance(module, torch.nn.Conv3d)]
    if not layers:
        raise ValueError("the model does not contain a Conv3d layer")
    return layers[-1]


class _SegmentationScore:
    """Adapt dense segmentation logits to one scalar target per sample."""

    def __init__(self, network, foreground_class: int, roi_mask=None):
        self.network = network
        self.foreground_class = foreground_class
        self.roi_mask = roi_mask

    def __call__(self, inputs):
        import torch

        logits: Any = self.network(inputs)
        if isinstance(logits, (tuple, list)):
            logits = logits[0]
        probabilities = (
            torch.sigmoid(logits[:, 0])
            if logits.shape[1] == 1
            else torch.softmax(logits, dim=1)[:, self.foreground_class]
        )
        if self.roi_mask is None:
            flat = probabilities.flatten(1)
            top_count = max(1, int(flat.shape[1] * 0.001))
            score = flat.topk(top_count, dim=1).values.mean(dim=1)
        else:
            mask = self.roi_mask.to(device=probabilities.device, dtype=probabilities.dtype)
            if mask.ndim == probabilities.ndim - 1:
                pass
            elif mask.ndim == probabilities.ndim:
                mask = mask[:, 0]
            else:
                raise ValueError("ROI mask dimensions do not match the model output")
            denominator = mask.flatten(1).sum(dim=1).clamp_min(1)
            score = (probabilities * mask).flatten(1).sum(dim=1) / denominator
        return score[:, None]


class GradCam3D:
    """Generate a normalized 3-D LayerGradCam attribution volume."""

    def __init__(self, network, target_layer=None, foreground_class: int = 1):
        self.network = network
        self.target_layer = target_layer or find_last_conv3d(network)
        self.foreground_class = foreground_class

    def attribute(self, inputs, roi_mask=None):
        import torch
        from captum.attr import LayerGradCam

        wrapped = _SegmentationScore(self.network, self.foreground_class, roi_mask)
        was_training = self.network.training
        self.network.eval()
        try:
            # MOSEC/nn/offline predictors commonly wrap the request in
            # torch.inference_mode(). enable_grad() alone does not override it.
            with torch.inference_mode(False), torch.enable_grad():
                tensor = inputs.detach().clone().requires_grad_(True)
                attribution = LayerGradCam(wrapped, self.target_layer).attribute(tensor, target=0)
                attribution = torch.relu(attribution)
                attribution = torch.nn.functional.interpolate(
                    attribution,
                    size=tensor.shape[2:],
                    mode="trilinear",
                    align_corners=False,
                )
                attribution = attribution.mean(dim=1, keepdim=True)
                flat = attribution.flatten(1)
                minimum = flat.min(dim=1).values[:, None, None, None, None]
                maximum = flat.max(dim=1).values[:, None, None, None, None]
                return ((attribution - minimum) / (maximum - minimum).clamp_min(1e-8)).detach()
        finally:
            self.network.train(was_training)
