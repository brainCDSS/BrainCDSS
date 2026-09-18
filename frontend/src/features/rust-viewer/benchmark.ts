import { cmapper } from "@niivue/niivue";
import type { LoadedViewer } from "./types";

export interface BenchmarkRow { operation: string; jsMs: number; wasmMs: number }
const TURBO = new Uint8Array(cmapper.colormap("turbo"));
const f32 = Math.fround;
const median = (values: number[]) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
function measure(operation: () => unknown, rounds = 21) { const values: number[] = []; for (let i = 0; i < rounds + 3; i += 1) { const start = performance.now(); operation(); if (i >= 3) values.push(performance.now() - start); } return median(values); }
function normalized(value: number, window: number, level: number) { const low = f32(f32(level) - f32(f32(window) / 2)); return Math.max(0, Math.min(1, f32(f32(value - low) / f32(window)))); }
function probabilityOffset(value: number) { const scaled = f32(f32(f32(value - f32(.15)) / f32(.85)) * 255); return Math.round(Math.max(0, Math.min(255, scaled))) * 4; }
function blend(base: number, color: number, opacity: number) { return Math.round(f32(f32(f32(base) * f32(1 - f32(opacity))) + f32(f32(color) * f32(opacity)))); }
function assertEqual(operation: string, js: ArrayLike<number>, wasm: ArrayLike<number>) { if (js.length !== wasm.length) throw new Error(`${operation}: output length mismatch`); for (let i = 0; i < js.length; i += 1) if (js[i] !== wasm[i]) throw new Error(`${operation}: output mismatch at byte ${i} (${js[i]} !== ${wasm[i]})`); }

export function runBenchmark(loaded: LoadedViewer, index: number): BenchmarkRow[] {
  const { source, mask, probability, engine } = loaded; const area = source.dimensions[0] * source.dimensions[1]; const offset = area * index;
  const slice = source.voxels.subarray(offset, offset + area); const maskSlice = mask?.voxels.subarray(offset, offset + area); const probabilitySlice = probability?.voxels.subarray(offset, offset + area);
  const window = f32(source.window), level = f32(source.level), maskOpacity = f32(mask ? .5 : 0), probabilityOpacity = f32(probability ? .5 : 0);
  const jsSlice = () => source.voxels.slice(offset, offset + area);
  const jsWindow = () => { const output = new Uint8Array(area); for (let i = 0; i < area; i += 1) output[i] = Math.round(f32(normalized(slice[i], window, level) * 255)); return output; };
  const jsMask = () => { const output = new Uint8Array(area * 4); for (let i = 0; i < area; i += 1) { output[i * 4] = 255; output[i * 4 + 3] = maskSlice![i] >= .5 ? Math.round(f32(maskOpacity * 255)) : 0; } return output; };
  const jsProbability = () => { const output = new Uint8Array(area * 4); for (let i = 0; i < area; i += 1) { const p = probabilityOffset(probabilitySlice![i]); output.set(TURBO.subarray(p, p + 3), i * 4); output[i * 4 + 3] = probabilitySlice![i] >= f32(.15) ? Math.round(f32(probabilityOpacity * 255)) : 0; } return output; };
  const jsComposite = () => { const output = new Uint8Array(area * 4); for (let i = 0; i < area; i += 1) { const gray = Math.round(f32(normalized(slice[i], window, level) * 255)); let red = gray, green = gray, blue = gray; if (probabilitySlice && probabilitySlice[i] >= f32(.15)) { const p = probabilityOffset(probabilitySlice[i]); red = blend(red, TURBO[p], probabilityOpacity); green = blend(green, TURBO[p + 1], probabilityOpacity); blue = blend(blue, TURBO[p + 2], probabilityOpacity); } if (maskSlice && maskSlice[i] >= .5) { red = blend(red, 255, maskOpacity); green = blend(green, 0, maskOpacity); blue = blend(blue, 0, maskOpacity); } output.set([red, green, blue, 255], i * 4); } return output; };
  const rows: Array<[string, () => ArrayLike<number>, () => ArrayLike<number>]> = [["Slice extraction", jsSlice, () => engine.extract_axial_slice(index)], ["Window / Level", jsWindow, () => engine.window_slice(index, window, level)]];
  if (maskSlice) rows.push(["Segmentation RGBA", jsMask, () => engine.segmentation_slice(index, maskOpacity)]);
  if (probabilitySlice) rows.push(["Probability RGBA + LUT", jsProbability, () => engine.probability_slice(index, probabilityOpacity, TURBO)]);
  rows.push(["Full composite RGBA", jsComposite, () => engine.render_slice(index, window, level, maskOpacity, probabilityOpacity, TURBO)]);
  return rows.map(([operation, jsOperation, wasmOperation]) => { assertEqual(operation, jsOperation(), wasmOperation()); return { operation, jsMs: measure(jsOperation), wasmMs: measure(wasmOperation) }; });
}
