import type { WasmModule } from "../types";

let initialized: Promise<{ module: WasmModule; initMs: number }> | undefined;
export function loadWasm() {
  initialized ??= (async () => {
    const start = performance.now();
    try {
      const module = await import("./generated/brainon_rust_viewer.js") as WasmModule;
      await module.default();
      return { module, initMs: performance.now() - start };
    } catch {
      initialized = undefined;
      throw new Error("Rust/WASM 모듈을 불러오지 못했습니다. npm run build:rust-viewer 실행 후 다시 시도하세요.");
    }
  })();
  return initialized;
}
