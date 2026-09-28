import { NVImage } from "@niivue/niivue";
import { authenticatedAsset } from "../../api/client";
import type { VolumeData } from "./types";

export async function loadVolume(url: string, role: string): Promise<VolumeData> {
  const image = await NVImage.loadFromUrl({ ...authenticatedAsset(url), name: `${role.toLowerCase()}.nii.gz` });
  if (!image.hdr || !image.dimsRAS || !image.pixDimsRAS || !image.matRAS) throw new Error("NIfTI geometry가 없습니다.");
  if (image.hdr.dims[0] > 3 && image.hdr.dims.slice(4, 8).some((n) => n > 1)) throw new Error("Beta v1은 단일 3D scalar volume만 지원합니다.");
  const dimensions = image.dimsRAS.slice(1, 4) as [number, number, number];
  const spacing = image.pixDimsRAS.slice(1, 4).map(Math.abs) as [number, number, number];
  if (spacing.some((n) => !Number.isFinite(n) || n <= 0)) throw new Error("잘못된 voxel spacing입니다.");
  // The production viewer uses this exact affine permutation/flip implementation.
  const ras = image.img2RAS();
  const rawSlope = Number(image.hdr.scl_slope);
  const slope = Number.isFinite(rawSlope) && rawSlope !== 0 ? rawSlope : 1;
  const rawIntercept = Number(image.hdr.scl_inter);
  const intercept = Number.isFinite(rawIntercept) ? rawIntercept : 0;
  const voxels = new Float32Array(ras.length);
  let dataMinimum = Number.POSITIVE_INFINITY; let dataMaximum = Number.NEGATIVE_INFINITY;
  for (let i = 0; i < ras.length; i++) { const value = ras[i] * slope + intercept; voxels[i] = value; dataMinimum = Math.min(dataMinimum, value); dataMaximum = Math.max(dataMaximum, value); }
  let minimum = Number(image.cal_min); let maximum = Number(image.cal_max);
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || maximum <= minimum) { minimum = Number(image.robust_min); maximum = Number(image.robust_max); }
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || maximum <= minimum) { minimum = dataMinimum; maximum = dataMaximum; }
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || maximum <= minimum) { minimum = 0; maximum = 1; }
  return { dimensions, spacing, affine: Array.from(image.matRAS), voxels, voxelType: ras.constructor.name,
    window: role === "CT" ? 80 : Math.max(0.001, maximum - minimum), level: role === "CT" ? 40 : (minimum + maximum) / 2 };
}
export function assertAligned(source: VolumeData, overlay: VolumeData) {
  const close = (a: number[], b: number[], tolerance: number) => a.length === b.length && a.every((n, i) => Math.abs(n - b[i]) <= tolerance);
  if (!close(source.dimensions, overlay.dimensions, 0) || !close(source.spacing, overlay.spacing, 0.001) || !close(source.affine, overlay.affine, 0.001)) {
    throw new Error("오버레이 shape·affine·spacing이 원본과 다릅니다. Beta의 표시를 중지했습니다.");
  }
}
