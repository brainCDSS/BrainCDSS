"""End-to-end nnU-Net inference orchestration."""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from itertools import permutations
from pathlib import Path
from uuid import uuid4

from src.errors import InferenceServiceError, ModelNotReadyError
from src.model_loader import ManifestModelLoader
from src.schemas import InferenceRequest, InferenceResponse, ModelInfo, OutputObject
from src.storage import GCSStorage


class InferenceService:
    def __init__(
        self,
        storage: GCSStorage,
        loader: ManifestModelLoader,
        work_root: Path,
        result_bucket: str,
    ):
        self.storage = storage
        self.loader = loader
        self.work_root = work_root
        self.result_bucket = result_bucket

        self._predictors = {}
        self._predictor_lock = threading.Lock()

    def readiness(self) -> dict:
        reasons = []

        try:
            import torch
            import nnunetv2  # noqa: F401
            import nibabel  # noqa: F401

            if not torch.cuda.is_available():
                reasons.append("CUDA_NOT_AVAILABLE")

        except ImportError as exc:
            reasons.append(f"DEPENDENCY_MISSING:{exc.name}")

        return {
            "ready": not reasons,
            "reasons": reasons,
        }

    def release_predictors(self) -> None:
        """Release GPU model caches after a MOSEC request completes."""
        import gc

        with self._predictor_lock:
            self._predictors.clear()
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def execute(self, request: InferenceRequest) -> InferenceResponse:
        started = time.perf_counter()
        trace_id = request.trace_id or str(uuid4())

        timing = {}

        work_dir = (
            self.work_root
            / str(request.analysis_id)
            / f"attempt-{request.attempt}"
        )

        if work_dir.exists():
            shutil.rmtree(work_dir)

        work_dir.mkdir(parents=True)

        try:
            # ---------------------------------------------------------
            # 1. Model bundle / predictor load
            # ---------------------------------------------------------
            load_started = time.perf_counter()

            manifest, bundle_dir, manifest_uri = self.loader.prepare(
                request.model_selector,
                request.analysis_type,
            )

            predictor = self._get_predictor(
                manifest,
                bundle_dir,
            )

            timing["load"] = _milliseconds(load_started)

            # ---------------------------------------------------------
            # 2. Input download
            # ---------------------------------------------------------
            download_started = time.perf_counter()

            input_paths = []

            for index, item in enumerate(request.inputs):
                path = (
                    work_dir
                    / "inputs"
                    / f"case_000{index}.nii.gz"
                )

                self.storage.download(
                    item.uri,
                    path,
                    size_bytes=item.size_bytes,
                    sha256=item.sha256,
                )

                input_paths.append(path)

            timing["download"] = _milliseconds(download_started)

            # ---------------------------------------------------------
            # 3. Input geometry validation
            # ---------------------------------------------------------
            preprocess_started = time.perf_counter()

            self._validate_geometry(
                request,
                input_paths,
            )

            timing["preprocess"] = _milliseconds(preprocess_started)

            # ---------------------------------------------------------
            # 4. nnU-Net inference
            # ---------------------------------------------------------
            inference_started = time.perf_counter()

            output_dir = work_dir / "outputs"
            output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            # nnU-Net export는 dataset.json의 file_ending을
            # 자동으로 붙이기 때문에 확장자가 없는 경로를 전달한다.
            mask_truncated = output_dir / "mask"

            if not hasattr(
                predictor,
                "predict_from_files_sequential",
            ):
                raise ModelNotReadyError(
                    "installed nnU-Net does not provide "
                    "predict_from_files_sequential"
                )

            # MOSEC Worker는 daemon process이므로
            # multiprocessing 기반 predict_from_files()를 사용하면
            # "daemonic processes are not allowed to have children"
            # 오류가 발생한다.
            #
            # 따라서 multiprocessing을 사용하지 않는
            # sequential API를 사용한다.
            predictor.predict_from_files_sequential(
                [
                    [
                        str(path)
                        for path in input_paths
                    ]
                ],
                [str(mask_truncated)],
                # nnU-Net already produces the foreground softmax values during
                # segmentation. Keep that export so the viewer can show a
                # lesion-probability map without running the model a second time.
                save_probabilities=True,
                overwrite=True,
            )

            file_ending = predictor.dataset_json.get(
                "file_ending",
                ".nii.gz",
            )

            mask_path = Path(
                str(mask_truncated) + file_ending
            )

            if not mask_path.is_file():
                raise InferenceServiceError(
                    "INFERENCE_FAILED",
                    f"nnU-Net did not create a mask: {mask_path}",
                )

            probability_path = output_dir / "lesion-probability.nii.gz"
            probability_metadata = self._export_probability_map(
                Path(str(mask_truncated) + ".npz"),
                mask_path,
                probability_path,
            )

            timing["inference"] = _milliseconds(
                inference_started
            )

            # ---------------------------------------------------------
            # 5. Post-processing / result JSON
            # ---------------------------------------------------------
            post_started = time.perf_counter()

            metrics, geometry = self._summarize(
                mask_path
            )

            xai_path = output_dir / "integrated-gradients.nii.gz"
            xai_metadata = None
            xai_error = None
            if os.getenv("XAI_ENABLED", "true").lower() in {"1", "true", "yes"}:
                xai_started = time.perf_counter()
                try:
                    from src.xai.nnunet_integrated_gradients import generate_nnunet_integrated_gradients

                    xai_metadata = generate_nnunet_integrated_gradients(
                        predictor,
                        input_paths,
                        input_paths[0],
                        xai_path,
                    )
                except Exception as exc:  # XAI is optional; segmentation remains usable.
                    xai_error = f"{type(exc).__name__}: {exc}"
                timing["xai"] = _milliseconds(xai_started)

            result_path = (
                work_dir
                / "outputs"
                / "result.json"
            )

            result_payload = {
                "schema_version": "1.0.0",
                "analysis_id": str(
                    request.analysis_id
                ),
                "analysis_type": (
                    request.analysis_type.value
                ),
                "attempt": int(
                    request.attempt
                ),
                "model_name": manifest[
                    "model_name"
                ],
                "model_version": manifest[
                    "bundle_id"
                ],
                "manifest_uri": manifest_uri,
                "metrics": metrics,
                "output_geometry": geometry,
                "probability_map": probability_metadata,
                "xai": xai_metadata,
                "xai_error": xai_error,
                "trace_id": trace_id,
            }

            result_path.write_text(
                json.dumps(
                    result_payload,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            timing["postprocess"] = _milliseconds(
                post_started
            )

            # ---------------------------------------------------------
            # 6. Upload outputs to GCS
            # ---------------------------------------------------------
            upload_started = time.perf_counter()

            prefix = (
                f"gs://{self.result_bucket}"
                f"/results/{request.analysis_id}"
                f"/attempt-{request.attempt}"
            )

            mask_info = self.storage.upload(
                mask_path,
                f"{prefix}/mask.nii.gz",
            )

            result_info = self.storage.upload(
                result_path,
                f"{prefix}/result.json",
                content_type="application/json",
            )

            xai_info = (
                self.storage.upload(
                    xai_path,
                    f"{prefix}/integrated-gradients.nii.gz",
                )
                if xai_metadata is not None and xai_path.is_file()
                else None
            )

            probability_info = (
                self.storage.upload(
                    probability_path,
                    f"{prefix}/lesion-probability.nii.gz",
                )
                if probability_metadata is not None and probability_path.is_file()
                else None
            )

            timing["upload"] = _milliseconds(
                upload_started
            )

            timing["total"] = _milliseconds(
                started
            )

            mlflow = manifest.get("mlflow") or {}

            # ---------------------------------------------------------
            # 7. Final response
            # ---------------------------------------------------------
            return InferenceResponse(
                analysis_id=request.analysis_id,
                analysis_type=request.analysis_type,
                attempt=request.attempt,
                status="SUCCEEDED",
                model=ModelInfo(
                    name=manifest["model_name"],
                    version=manifest["bundle_id"],
                    mlflow_run_id=mlflow.get(
                        "run_id"
                    ),
                    manifest_uri=manifest_uri,
                ),
                outputs=[
                    OutputObject(
                        type="NIFTI_MASK",
                        **mask_info.__dict__,
                    ),
                    OutputObject(
                        type="RESULT_JSON",
                        **result_info.__dict__,
                    ),
                    *(
                        [OutputObject(type="LESION_PROBABILITY_NIFTI", **probability_info.__dict__)]
                        if probability_info is not None
                        else []
                    ),
                    *(
                        [OutputObject(type="INTEGRATED_GRADIENTS_NIFTI", **xai_info.__dict__)]
                        if xai_info is not None
                        else []
                    ),
                ],
                metrics=metrics,
                timing_ms=timing,
                error=None,
                trace_id=trace_id,
            )

        finally:
            if (
                os.getenv(
                    "KEEP_INFERENCE_TEMP",
                    "false",
                ).lower()
                != "true"
            ):
                shutil.rmtree(
                    work_dir,
                    ignore_errors=True,
                )

    def _get_predictor(
        self,
        manifest: dict,
        bundle_dir: Path,
    ):
        cache_key = (
            f"{manifest['model_name']}:"
            f"{manifest['bundle_id']}"
        )

        with self._predictor_lock:
            if cache_key in self._predictors:
                return self._predictors[
                    cache_key
                ]

            try:
                import torch

                from nnunetv2.inference.predict_from_raw_data import (
                    nnUNetPredictor,
                )

            except ImportError as exc:
                raise ModelNotReadyError(
                    "nnU-Net runtime dependency is missing"
                ) from exc

            if not torch.cuda.is_available():
                raise ModelNotReadyError(
                    "CUDA GPU is not available"
                )

            trainer_dir = (
                bundle_dir
                / "trainer"
            )

            current = [
                entry
                for entry in os.getenv(
                    "nnUNet_extTrainer",
                    "",
                ).split(os.pathsep)
                if entry
            ]

            if str(trainer_dir) not in current:
                current.insert(
                    0,
                    str(trainer_dir),
                )

                os.environ[
                    "nnUNet_extTrainer"
                ] = os.pathsep.join(
                    current
                )

            predictor = nnUNetPredictor(
                tile_step_size=0.5,
                use_gaussian=True,
                use_mirroring=True,
                perform_everything_on_device=True,
                device=torch.device("cuda"),
                verbose=False,
                verbose_preprocessing=False,
                allow_tqdm=False,
            )

            training_config = manifest.get("training_config")
            if training_config:
                config_path = (bundle_dir / training_config).resolve()
                if not config_path.is_file() or bundle_dir.resolve() not in config_path.parents:
                    raise ModelNotReadyError(
                        "model training config is missing",
                        detail={"training_config": training_config},
                    )
                os.environ["ICH_NNUNET_CONFIG"] = str(config_path)

            predictor.initialize_from_trained_model_folder(
                str(bundle_dir),
                use_folds=tuple(
                    manifest["nnunet"].get(
                        "folds",
                        [0],
                    )
                ),
                checkpoint_name=Path(
                    manifest["checkpoint"]
                ).name,
            )

            self._predictors.clear()

            self._predictors[
                cache_key
            ] = predictor

            return predictor

    @staticmethod
    def _validate_geometry(
        request: InferenceRequest,
        paths: list[Path],
    ):
        # DWI + ADC처럼 2채널인 경우에만
        # geometry 일치 여부를 확인한다.
        if len(paths) != 2:
            return

        import nibabel as nib
        import numpy as np

        dwi, adc = (
            nib.load(str(path))
            for path in paths
        )

        if (
            dwi.shape != adc.shape
            or not np.allclose(
                dwi.affine,
                adc.affine,
                atol=1e-5,
            )
        ):
            raise InferenceServiceError(
                "INPUT_GEOMETRY_MISMATCH",
                "DWI and ADC geometry must match",
            )

    @staticmethod
    def _summarize(
        mask_path: Path,
    ):
        import nibabel as nib
        import numpy as np

        image = nib.load(
            str(mask_path)
        )

        data = np.asarray(
            image.dataobj
        )

        lesion_voxels = int(
            np.count_nonzero(data)
        )

        voxel_volume_mm3 = float(
            abs(
                np.linalg.det(
                    image.affine[:3, :3]
                )
            )
        )

        labels, counts = np.unique(
            data,
            return_counts=True,
        )

        # JSON serialization 오류 방지를 위해
        # NumPy scalar를 모두 Python 기본 타입으로 변환한다.
        metrics = {
            "lesion_voxels": int(
                lesion_voxels
            ),
            "volume_ml": float(
                lesion_voxels
                * voxel_volume_mm3
                / 1000.0
            ),
            "labels": {
                str(int(label)): int(count)
                for label, count in zip(
                    labels,
                    counts,
                )
            },
        }
        metrics["lesions"] = InferenceService._summarize_lesions(
            data,
            voxel_volume_mm3,
        )
        metrics["lesion_count"] = len(metrics["lesions"])

        geometry = {
            "shape": [
                int(value)
                for value in image.shape
            ],
            "spacing": [
                float(value)
                for value in image.header.get_zooms()[:3]
            ],
            "affine": [
                [
                    float(value)
                    for value in row
                ]
                for row in image.affine
            ],
        }

        return (
            metrics,
            geometry,
        )

    @staticmethod
    def _summarize_lesions(
        mask,
        voxel_volume_mm3: float,
    ) -> list[dict]:
        """Describe actual 3-D connected components from the saved mask.

        This deliberately reports segmentation geometry only. It does not
        infer an anatomical location or diagnostic subtype without a validated
        atlas/clinical model. ``representative_slice`` is a one-based axial
        NIfTI slice index with the largest component area and can drive the
        viewer directly.
        """
        import numpy as np
        from scipy import ndimage

        foreground = np.asarray(mask) != 0
        if foreground.ndim != 3 or not foreground.any():
            return []
        labels, count = ndimage.label(
            foreground,
            structure=np.ones((3, 3, 3), dtype=np.uint8),
        )
        total_voxels = int(foreground.sum())
        lesions = []
        for label_id in range(1, count + 1):
            component = labels == label_id
            voxel_count = int(component.sum())
            if not voxel_count:
                continue
            axial_counts = component.sum(axis=(0, 1))
            representative_slice = int(np.argmax(axial_counts)) + 1
            lesions.append(
                {
                    "id": int(label_id),
                    "voxel_count": voxel_count,
                    "volume_ml": float(voxel_count * voxel_volume_mm3 / 1000.0),
                    "relative_volume_pct": float(voxel_count * 100.0 / total_voxels),
                    "representative_slice": representative_slice,
                }
            )
        return sorted(lesions, key=lambda item: item["volume_ml"], reverse=True)

    @staticmethod
    def _export_probability_map(
        probabilities_path: Path,
        reference_path: Path,
        output_path: Path,
    ) -> dict | None:
        """Export nnU-Net foreground softmax values in source NIfTI space.

        ``predict_from_files_sequential(save_probabilities=True)`` writes an
        NPZ next to the segmentation. The exporter has already restored those
        probabilities to the same voxel grid as the mask, so this conversion
        must preserve the reference affine rather than resample or invent an
        alignment transform.
        """
        if not probabilities_path.is_file():
            return None

        import nibabel as nib
        import numpy as np

        with np.load(probabilities_path) as archive:
            probabilities = np.asarray(archive["probabilities"], dtype=np.float32)
        if probabilities.ndim != 4 or probabilities.shape[0] < 2:
            raise InferenceServiceError(
                "INVALID_PROBABILITY_OUTPUT",
                "nnU-Net probability export must contain background and foreground channels",
            )

        # Multi-label models can have more than one foreground channel. The
        # displayed map answers one stable clinical question: probability that
        # this voxel belongs to any predicted lesion label.
        foreground = np.max(probabilities[1:], axis=0).astype(np.float32)
        reference = nib.load(str(reference_path))
        foreground = InferenceService._match_reference_axes(
            foreground,
            tuple(reference.shape[:3]),
        )
        header = reference.header.copy()
        header.set_data_dtype(np.float32)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        nib.save(
            nib.Nifti1Image(foreground, reference.affine, header),
            str(output_path),
        )
        return {
            "type": "LESION_PROBABILITY_NIFTI",
            "semantics": "VOXELWISE_FOREGROUND_PROBABILITY",
            "normalization": "MODEL_INFERENCE_PROBABILITY_0_1",
            "foreground_channels": int(probabilities.shape[0] - 1),
        }

    @staticmethod
    def _match_reference_axes(
        volume,
        reference_shape: tuple[int, int, int],
    ):
        """Match nnU-Net's image-reader axis order to a written NIfTI mask."""
        import numpy as np

        array = np.asarray(volume, dtype=np.float32)
        if tuple(array.shape) == reference_shape:
            return array
        reversed_array = array.transpose(tuple(reversed(range(array.ndim))))
        if tuple(reversed_array.shape) == reference_shape:
            return reversed_array
        candidates = [
            axes for axes in permutations(range(array.ndim))
            if tuple(array.shape[index] for index in axes) == reference_shape
        ]
        if len(candidates) == 1:
            return array.transpose(candidates[0])
        raise InferenceServiceError(
            "PROBABILITY_GEOMETRY_MISMATCH",
            "nnU-Net probability grid cannot be matched to the NIfTI mask grid",
            detail={"probability_shape": list(array.shape), "mask_shape": list(reference_shape)},
        )


def _milliseconds(
    started: float,
) -> float:
    return float(
        round(
            (
                time.perf_counter()
                - started
            )
            * 1000.0,
            3,
        )
    )
