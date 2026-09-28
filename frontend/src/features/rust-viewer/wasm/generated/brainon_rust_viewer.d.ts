/* tslint:disable */
/* eslint-disable */

export class WasmVolume {
    free(): void;
    [Symbol.dispose](): void;
    extract_axial_slice(index: number): Float32Array;
    constructor(width: number, height: number, depth: number, voxels: Float32Array);
    probability_slice(index: number, opacity: number, lut: Uint8Array): Uint8Array;
    render_slice(index: number, window: number, level: number, mask_opacity: number, probability_opacity: number, lut: Uint8Array): Uint8Array;
    segmentation_slice(index: number, opacity: number): Uint8Array;
    set_mask(width: number, height: number, depth: number, voxels: Float32Array): void;
    set_probability(width: number, height: number, depth: number, voxels: Float32Array): void;
    window_slice(index: number, window: number, level: number): Uint8Array;
}

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
    readonly memory: WebAssembly.Memory;
    readonly __wbg_wasmvolume_free: (a: number, b: number) => void;
    readonly wasmvolume_extract_axial_slice: (a: number, b: number) => [number, number, number, number];
    readonly wasmvolume_new: (a: number, b: number, c: number, d: number, e: number) => [number, number, number];
    readonly wasmvolume_probability_slice: (a: number, b: number, c: number, d: number, e: number) => [number, number, number, number];
    readonly wasmvolume_render_slice: (a: number, b: number, c: number, d: number, e: number, f: number, g: number, h: number) => [number, number, number, number];
    readonly wasmvolume_segmentation_slice: (a: number, b: number, c: number) => [number, number, number, number];
    readonly wasmvolume_set_mask: (a: number, b: number, c: number, d: number, e: number, f: number) => [number, number];
    readonly wasmvolume_set_probability: (a: number, b: number, c: number, d: number, e: number, f: number) => [number, number];
    readonly wasmvolume_window_slice: (a: number, b: number, c: number, d: number) => [number, number, number, number];
    readonly __wbindgen_externrefs: WebAssembly.Table;
    readonly __externref_table_dealloc: (a: number) => void;
    readonly __wbindgen_free: (a: number, b: number, c: number) => void;
    readonly __wbindgen_malloc: (a: number, b: number) => number;
    readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;

/**
 * Instantiates the given `module`, which can either be bytes or
 * a precompiled `WebAssembly.Module`.
 *
 * @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
 *
 * @returns {InitOutput}
 */
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
 * If `module_or_path` is {RequestInfo} or {URL}, makes a request and
 * for everything else, calls `WebAssembly.instantiate` directly.
 *
 * @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
 *
 * @returns {Promise<InitOutput>}
 */
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
