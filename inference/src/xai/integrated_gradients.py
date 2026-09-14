"""Smooth Integrated Gradients for predicted-lesion 3-D segmentation targets."""

from __future__ import annotations

from .gradcam import _SegmentationScore


class IntegratedGradients3D:
    """Attribute input voxels to the predicted lesion foreground-logit score."""

    def __init__(self, network, foreground_class: int = 1):
        self.network = network
        self.foreground_class = foreground_class

    def attribute(self, inputs, roi_mask, steps: int = 8, smooth_samples: int = 4, noise_std: float = 0.05):
        import torch
        from captum.attr import IntegratedGradients

        wrapped = _SegmentationScore(self.network, self.foreground_class, roi_mask)
        was_training = self.network.training
        self.network.eval()
        try:
            with torch.inference_mode(False), torch.enable_grad():
                tensor = inputs.detach().clone().requires_grad_(True)
                # Do not let NoiseTunnel expand all SmoothGrad samples into one
                # GPU batch. Full 3-D nnU-Net patches exceed GPU memory that way.
                # Running samples one at a time is slower but bounded in memory.
                integrated_gradients = IntegratedGradients(wrapped)
                attribution = torch.zeros_like(tensor)
                for _ in range(smooth_samples):
                    noisy = tensor + torch.randn_like(tensor) * noise_std
                    sample = integrated_gradients.attribute(
                        noisy,
                        baselines=torch.zeros_like(tensor),
                        target=0,
                        n_steps=steps,
                        internal_batch_size=1,
                    )
                    attribution += sample.square()
                attribution /= smooth_samples
                # Positive magnitude means the input voxel affects the ROI logit;
                # it is not clipped by the predicted segmentation mask.
                return attribution.abs().mean(dim=1, keepdim=True).detach()
        finally:
            self.network.train(was_training)
