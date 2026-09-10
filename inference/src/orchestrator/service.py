"""End-to-end nnU-Net inference orchestration."""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from pathlib import Path
from uuid import uuid4

from src.errors import InferenceServiceError, ModelNotReadyError
from src.model_loader import ManifestModelLoader
from src.schemas import InferenceRequest, InferenceResponse, ModelInfo, OutputObject
from src.storage import GCSStorage


class InferenceService:
    def __init__(self, storage: GCSStorage, loader: ManifestModelLoader, work_root: Path, result_bucket: str):
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
        return {"ready": not reasons, "reasons": reasons}

    def execute(self, request: InferenceRequest) -> InferenceResponse:
        started = time.perf_counter()
        trace_id = request.trace_id or str(uuid4())
        timing = {}
        work_dir = self.work_root / str(request.analysis_id) / f"attempt-{request.attempt}"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True)
        try:
            load_started = time.perf_counter()
            manifest, bundle_dir, manifest_uri = self.loader.prepare(
                request.model_selector, request.analysis_type
            )
            predictor = self._get_predictor(manifest, bundle_dir)
            timing["load"] = _milliseconds(load_started)

            download_started = time.perf_counter()
            input_paths = []
            for index, item in enumerate(request.inputs):
                path = work_dir / "inputs" / f"case_000{index}.nii.gz"
                self.storage.download(
                    item.uri, path, size_bytes=item.size_bytes, sha256=item.sha256
                )
                input_paths.append(path)
            timing["download"] = _milliseconds(download_started)

            preprocess_started = time.perf_counter()
            self._validate_geometry(request, input_paths)
            timing["preprocess"] = _milliseconds(preprocess_started)

            inference_started = time.perf_counter()
            mask_path = work_dir / "outputs" / "mask.nii.gz"
            mask_path.parent.mkdir(parents=True)
            predictor.predict_from_files(
                [[str(path) for path in input_paths]],
                [str(mask_path)],
                save_probabilities=False,
                overwrite=True,
                num_processes_preprocessing=1,
                num_processes_segmentation_export=1,
            )
            if not mask_path.is_file():
                raise InferenceServiceError("INFERENCE_FAILED", "nnU-Net did not create a mask")
            timing["inference"] = _milliseconds(inference_started)

            post_started = time.perf_counter()
            metrics, geometry = self._summarize(mask_path)
            result_path = work_dir / "outputs" / "result.json"
            result_payload = {
                "schema_version": "1.0.0",
                "analysis_id": str(request.analysis_id),
                "analysis_type": request.analysis_type.value,
                "attempt": request.attempt,
                "model_name": manifest["model_name"],
                "model_version": manifest["bundle_id"],
                "manifest_uri": manifest_uri,
                "metrics": metrics,
                "output_geometry": geometry,
                "trace_id": trace_id,
            }
            result_path.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
            timing["postprocess"] = _milliseconds(post_started)

            upload_started = time.perf_counter()
            prefix = (
                f"gs://{self.result_bucket}/results/{request.analysis_id}"
                f"/attempt-{request.attempt}"
            )
            mask_info = self.storage.upload(mask_path, f"{prefix}/mask.nii.gz")
            result_info = self.storage.upload(
                result_path, f"{prefix}/result.json", content_type="application/json"
            )
            timing["upload"] = _milliseconds(upload_started)
            timing["total"] = _milliseconds(started)
            mlflow = manifest.get("mlflow") or {}
            return InferenceResponse(
                analysis_id=request.analysis_id,
                analysis_type=request.analysis_type,
                attempt=request.attempt,
                status="SUCCEEDED",
                model=ModelInfo(
                    name=manifest["model_name"],
                    version=manifest["bundle_id"],
                    mlflow_run_id=mlflow.get("run_id"),
                    manifest_uri=manifest_uri,
                ),
                outputs=[
                    OutputObject(type="NIFTI_MASK", **mask_info.__dict__),
                    OutputObject(type="RESULT_JSON", **result_info.__dict__),
                ],
                metrics=metrics,
                timing_ms=timing,
                error=None,
                trace_id=trace_id,
            )
        finally:
            if os.getenv("KEEP_INFERENCE_TEMP", "false").lower() != "true":
                shutil.rmtree(work_dir, ignore_errors=True)

    def _get_predictor(self, manifest: dict, bundle_dir: Path):
        cache_key = f"{manifest['model_name']}:{manifest['bundle_id']}"
        with self._predictor_lock:
            if cache_key in self._predictors:
                return self._predictors[cache_key]
            try:
                import torch
                from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
            except ImportError as exc:
                raise ModelNotReadyError("nnU-Net runtime dependency is missing") from exc
            if not torch.cuda.is_available():
                raise ModelNotReadyError("CUDA GPU is not available")
            trainer_dir = bundle_dir / "trainer"
            current = [entry for entry in os.getenv("nnUNet_extTrainer", "").split(os.pathsep) if entry]
            if str(trainer_dir) not in current:
                current.insert(0, str(trainer_dir))
                os.environ["nnUNet_extTrainer"] = os.pathsep.join(current)
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
            predictor.initialize_from_trained_model_folder(
                str(bundle_dir),
                use_folds=tuple(manifest["nnunet"].get("folds", [0])),
                checkpoint_name=Path(manifest["checkpoint"]).name,
            )
            self._predictors.clear()
            self._predictors[cache_key] = predictor
            return predictor

    @staticmethod
    def _validate_geometry(request: InferenceRequest, paths: list[Path]):
        if len(paths) != 2:
            return
        import nibabel as nib
        import numpy as np

        dwi, adc = (nib.load(str(path)) for path in paths)
        if dwi.shape != adc.shape or not np.allclose(dwi.affine, adc.affine, atol=1e-5):
            raise InferenceServiceError(
                "INPUT_GEOMETRY_MISMATCH", "DWI and ADC geometry must match"
            )

    @staticmethod
    def _summarize(mask_path: Path):
        import nibabel as nib
        import numpy as np

        image = nib.load(str(mask_path))
        data = np.asarray(image.dataobj)
        lesion_voxels = int(np.count_nonzero(data))
        voxel_volume_mm3 = float(abs(np.linalg.det(image.affine[:3, :3])))
        labels, counts = np.unique(data, return_counts=True)
        return (
            {
                "lesion_voxels": lesion_voxels,
                "volume_ml": lesion_voxels * voxel_volume_mm3 / 1000.0,
                "labels": {str(int(label)): int(count) for label, count in zip(labels, counts)},
            },
            {
                "shape": list(image.shape),
                "spacing": list(image.header.get_zooms()[:3]),
                "affine": image.affine.tolist(),
            },
        )


def _milliseconds(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)
