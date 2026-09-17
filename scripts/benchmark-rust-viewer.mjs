import { readFile } from "node:fs/promises";
import { performance } from "node:perf_hooks";
import init, { WasmVolume } from "../frontend/src/features/rust-viewer/wasm/generated/brainon_rust_viewer.js";

await init({ module_or_path: await readFile(new URL("../frontend/src/features/rust-viewer/wasm/generated/brainon_rust_viewer_bg.wasm", import.meta.url)) });
const width = 128, height = 128, depth = 64, area = width * height, index = 32;
const source = new Float32Array(area * depth), mask = new Float32Array(source.length), probability = new Float32Array(source.length);
for (let i = 0; i < source.length; i += 1) { source[i] = (i % 4096) / 16; mask[i] = i % 97 === 0 ? 1 : 0; probability[i] = (i % 101) / 100; }
const lut = new Uint8Array(1024); for (let i = 0; i < 256; i += 1) lut.set([i, 255 - i, (i * 3) % 256, 255], i * 4);
const wasm = new WasmVolume(width, height, depth, source); wasm.set_mask(width, height, depth, mask); wasm.set_probability(width, height, depth, probability);
const f32 = Math.fround, offset = area * index, slice = source.subarray(offset, offset + area), maskSlice = mask.subarray(offset, offset + area), probSlice = probability.subarray(offset, offset + area);
const normalized = (value) => Math.max(0, Math.min(1, f32(f32(value) / f32(80))));
const probabilityOffset = (value) => Math.round(Math.max(0, Math.min(255, f32(f32(f32(value - f32(.15)) / f32(.85)) * 255)))) * 4;
const blend = (base, color, opacity) => Math.round(f32(f32(f32(base) * f32(1 - f32(opacity))) + f32(f32(color) * f32(opacity))));
const jsSlice = () => source.slice(offset, offset + area);
const jsWindow = () => { const out = new Uint8Array(area); for (let i = 0; i < area; i += 1) out[i] = Math.round(f32(normalized(slice[i]) * 255)); return out; };
const jsMask = () => { const out = new Uint8Array(area * 4); for (let i = 0; i < area; i += 1) { out[i * 4] = 255; out[i * 4 + 3] = maskSlice[i] >= .5 ? 128 : 0; } return out; };
const jsProbability = () => { const out = new Uint8Array(area * 4); for (let i = 0; i < area; i += 1) { const p = probabilityOffset(probSlice[i]); out.set(lut.subarray(p, p + 3), i * 4); out[i * 4 + 3] = probSlice[i] >= f32(.15) ? 128 : 0; } return out; };
const jsComposite = () => { const out = new Uint8Array(area * 4); for (let i = 0; i < area; i += 1) { const gray = Math.round(f32(normalized(slice[i]) * 255)); let r = gray, g = gray, b = gray; if (probSlice[i] >= f32(.15)) { const p = probabilityOffset(probSlice[i]); r = blend(r, lut[p], .5); g = blend(g, lut[p + 1], .5); b = blend(b, lut[p + 2], .5); } if (maskSlice[i] >= .5) { r = blend(r, 255, .5); g = blend(g, 0, .5); b = blend(b, 0, .5); } out.set([r, g, b, 255], i * 4); } return out; };
const median = (values) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
const measure = (fn) => { const values = []; for (let i = 0; i < 24; i += 1) { const start = performance.now(); fn(); if (i >= 3) values.push(performance.now() - start); } return median(values); };
const rows = [["Slice extraction", jsSlice, () => wasm.extract_axial_slice(index)], ["Window / Level", jsWindow, () => wasm.window_slice(index, 80, 40)], ["Segmentation RGBA", jsMask, () => wasm.segmentation_slice(index, .5)], ["Probability RGBA + LUT", jsProbability, () => wasm.probability_slice(index, .5, lut)], ["Full composite RGBA", jsComposite, () => wasm.render_slice(index, 80, 40, .5, .5, lut)]];
const assertEqual = (name, left, right) => { if (left.length !== right.length) throw new Error(`${name}: length mismatch`); for (let i = 0; i < left.length; i += 1) if (left[i] !== right[i]) throw new Error(`${name}: mismatch at ${i}: ${left[i]} !== ${right[i]}`); };
console.log(`Volume: ${width} x ${height} x ${depth}, Float32`); console.log("Operation\tJS (ms)\tRust/WASM (ms)");
for (const [name, js, rs] of rows) { assertEqual(name, js(), rs()); console.log(`${name}\t${measure(js).toFixed(3)}\t${measure(rs).toFixed(3)}`); }
wasm.free();
