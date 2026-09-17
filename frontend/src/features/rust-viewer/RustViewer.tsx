import { useCallback, useEffect, useMemo, useState } from "react";
import RustViewerCanvas, { type RenderMetrics } from "./RustViewerCanvas";
import { runBenchmark, type BenchmarkRow } from "./benchmark";
import { useRustViewer } from "./useRustViewer";
import "./rust-viewer.css";
import "./rust-viewer-overrides.css";

interface Props { analysisId?: string; studyId?: string }
export default function RustViewer({ analysisId, studyId }: Props) {
  const { loaded, loading, error, role, setRole, roles } = useRustViewer(analysisId, studyId);
  const [slice, setSlice] = useState(0), [window, setWindow] = useState(1), [level, setLevel] = useState(0);
  const [mask, setMask] = useState(true), [maskOpacity, setMaskOpacity] = useState(72);
  const [probability, setProbability] = useState(false), [probabilityOpacity, setProbabilityOpacity] = useState(48);
  const [renderError, setRenderError] = useState<string | null>(null), [benchmarks, setBenchmarks] = useState<BenchmarkRow[] | null>(null);
  const [renderMetrics, setRenderMetrics] = useState<RenderMetrics | null>(null);
  useEffect(() => { if (!loaded) return; setSlice(Math.floor(loaded.source.dimensions[2] / 2)); setWindow(loaded.source.window); setLevel(loaded.source.level); setBenchmarks(null); }, [loaded]);
  const onRenderError = useCallback((message: string) => setRenderError(message), []);
  const onRenderMetrics = useCallback((metrics: RenderMetrics) => setRenderMetrics(metrics), []);
  const settings = useMemo(() => ({ slice, window, level, maskOpacity: mask && loaded?.mask ? maskOpacity / 100 : 0, probabilityOpacity: probability && loaded?.probability ? probabilityOpacity / 100 : 0 }), [slice, window, level, mask, maskOpacity, probability, probabilityOpacity, loaded]);
  if (loading) return <section className="rust-viewer-card rust-viewer-state"><strong>Rust/WASM Viewer Beta</strong><span>WASM과 NIfTI volume을 준비하는 중입니다.</span></section>;
  if (error || !loaded) return <section className="rust-viewer-card rust-viewer-state is-error"><strong>Rust Viewer Beta를 열 수 없습니다.</strong><span>{error}</span></section>;
  const total = loaded.source.dimensions[2];
  return <section className="rust-viewer-card">
    <header className="rust-viewer-toolbar"><div><strong>Rust/WASM Viewer Beta</strong><span>RUST / WASM</span></div><div className="rust-viewer-channel">{roles.map((item) => <button type="button" key={item} className={role === item ? "is-active" : ""} onClick={() => setRole(item)}>{item}</button>)}</div></header>
    <div className="rust-viewer-controls">
      <label>Slice <input aria-label="slice" type="range" min="0" max={total - 1} value={slice} onChange={(event) => setSlice(Number(event.target.value))}/><output>{slice + 1} / {total}</output></label>
      <label>Window <input type="number" min="0.001" step="1" value={Number(window.toFixed(2))} onChange={(event) => setWindow(Math.max(.001, Number(event.target.value)))}/></label>
      <label>Level <input type="number" step="1" value={Number(level.toFixed(2))} onChange={(event) => setLevel(Number(event.target.value))}/></label>
      <label><input type="checkbox" checked={mask} disabled={!loaded.mask} onChange={(event) => setMask(event.target.checked)}/> 마스크</label><label>투명도 <input type="range" min="0" max="100" value={maskOpacity} disabled={!loaded.mask} onChange={(event) => setMaskOpacity(Number(event.target.value))}/><output>{maskOpacity}%</output></label>
      <label><input type="checkbox" checked={probability} disabled={!loaded.probability} onChange={(event) => setProbability(event.target.checked)}/> 가능도</label><label>투명도 <input type="range" min="0" max="100" value={probabilityOpacity} disabled={!loaded.probability} onChange={(event) => setProbabilityOpacity(Number(event.target.value))}/><output>{probabilityOpacity}%</output></label>
    </div>
    {renderError && <div className="rust-viewer-error">{renderError}</div>}
    <RustViewerCanvas loaded={loaded} settings={settings} onSlice={setSlice} onError={onRenderError} onMetrics={onRenderMetrics}/>
    <footer className="rust-viewer-footer"><span>Axial · Radiological RAS</span><span>{loaded.source.dimensions.join(" × ")} · {loaded.source.voxelType}</span><span>휠: 슬라이스 · 드래그: 이동</span><button type="button" onClick={() => setBenchmarks(runBenchmark(loaded, slice))}>Benchmark</button></footer>
    {benchmarks && <section className="rust-benchmark"><header><strong>현재 volume benchmark</strong><span>출력 바이트 일치 검증 · 중앙값 21회</span></header><table><thead><tr><th>Operation</th><th>JS</th><th>Rust/WASM</th></tr></thead><tbody>{benchmarks.map((row) => <tr key={row.operation}><td>{row.operation}</td><td>{row.jsMs.toFixed(3)} ms</td><td>{row.wasmMs.toFixed(3)} ms</td></tr>)}</tbody></table><small>WASM 초기화 {loaded.wasmInitMs.toFixed(2)} ms · volume load/변환 {loaded.volumeLoadMs.toFixed(2)} ms{renderMetrics ? ` · 최근 frame: WASM ${renderMetrics.wasmMs.toFixed(2)} / ImageData ${renderMetrics.imageDataMs.toFixed(2)} / Canvas ${renderMetrics.canvasMs.toFixed(2)} / 총 ${renderMetrics.totalMs.toFixed(2)} ms` : ""}</small></section>}
  </section>;
}
