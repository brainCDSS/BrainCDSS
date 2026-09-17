export interface WasmVolume {
  free(): void;
  set_mask(width: number, height: number, depth: number, voxels: Float32Array): void;
  set_probability(width: number, height: number, depth: number, voxels: Float32Array): void;
  extract_axial_slice(index: number): Float32Array;
  window_slice(index: number, window: number, level: number): Uint8Array;
  segmentation_slice(index: number, opacity: number): Uint8Array;
  probability_slice(index: number, opacity: number, lut: Uint8Array): Uint8Array;
  render_slice(index: number, window: number, level: number, maskOpacity: number, probabilityOpacity: number, lut: Uint8Array): Uint8Array;
}
export interface WasmModule {
  default(): Promise<unknown>;
  WasmVolume: new(width: number, height: number, depth: number, voxels: Float32Array) => WasmVolume;
}
export interface VolumeData {
  dimensions: [number, number, number];
  spacing: [number, number, number];
  affine: number[];
  voxels: Float32Array;
  voxelType: string;
  window: number;
  level: number;
}
export interface LoadedViewer {
  engine: WasmVolume;
  source: VolumeData;
  mask?: VolumeData;
  probability?: VolumeData;
  wasmInitMs: number;
  volumeLoadMs: number;
}
export interface RenderSettings { slice: number; window: number; level: number; maskOpacity: number; probabilityOpacity: number }
