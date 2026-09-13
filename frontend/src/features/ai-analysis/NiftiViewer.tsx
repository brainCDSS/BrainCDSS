import { useEffect, useRef, useState } from "react";
import { DRAG_MODE, MULTIPLANAR_TYPE, Niivue, SHOW_RENDER } from "@niivue/niivue";
import { authenticatedAsset } from "../../api/client";
import { getNiftiViewerManifest } from "./api";

type ViewMode = "AXIAL" | "CORONAL" | "SAGITTAL" | "MULTIPLANAR";
type Geometry = { shape: number[]; spacing: number[]; affine: number[] };
const MODES: Array<[ViewMode, string]> = [["AXIAL", "축상"], ["CORONAL", "관상"], ["SAGITTAL", "시상"], ["MULTIPLANAR", "멀티뷰"]];

function geometryOf(volume: Niivue["volumes"][number]): Geometry {
  return { shape: Array.from(volume.dimsRAS?.slice(1, 4) ?? []), spacing: Array.from(volume.pixDimsRAS?.slice(1, 4) ?? []), affine: Array.from(volume.matRAS ?? []) };
}
function sameGeometry(left: Geometry, right: Geometry) {
  const close = (a: number[], b: number[], tolerance: number) => a.length === b.length && a.every((value, index) => Math.abs(value - b[index]) <= tolerance);
  return close(left.shape, right.shape, 0) && close(left.spacing, right.spacing, 0.001) && close(left.affine, right.affine, 0.001);
}

export default function NiftiViewer({ analysisId, focusSlice }: { analysisId: string; focusSlice?: number | null }) {
  const shellRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewerRef = useRef<Niivue | null>(null);
  const maskIndexRef = useRef<number | null>(null);
  const modeRef = useRef<ViewMode>("AXIAL");
  const windowFrameRef = useRef<number | null>(null);
  const [message, setMessage] = useState("NIfTI 영상을 불러오는 중입니다.");
  const [sourceRole, setSourceRole] = useState("");
  const [hasMask, setHasMask] = useState(false);
  const [maskVisible, setMaskVisible] = useState(true);
  const [maskOpacity, setMaskOpacity] = useState(55);
  const [crosshairVisible, setCrosshairVisible] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("AXIAL");
  const [slice, setSlice] = useState({ current: 1, total: 1 });
  const [alignment, setAlignment] = useState<boolean | null>(null);
  const [windowing, setWindowing] = useState<{ level: number; width: number } | null>(null);

  function syncWindowing(volume: Niivue["volumes"][number] | undefined) {
    if (!volume || volume.cal_min == null || volume.cal_max == null) return;
    if (windowFrameRef.current !== null) cancelAnimationFrame(windowFrameRef.current);
    windowFrameRef.current = requestAnimationFrame(() => {
      const minimum = Number(volume.cal_min); const maximum = Number(volume.cal_max);
      setWindowing({ level: (minimum + maximum) / 2, width: maximum - minimum });
      windowFrameRef.current = null;
    });
  }

  function updateSlice(viewer: Niivue, mode = modeRef.current) {
    const dims = viewer.back?.dimsRAS;
    if (!dims || mode === "MULTIPLANAR") return setSlice({ current: 1, total: 1 });
    const axis = mode === "AXIAL" ? 2 : mode === "CORONAL" ? 1 : 0;
    const total = Number(dims[axis + 1] ?? 1);
    const current = Math.min(total, Math.max(1, Math.round(viewer.scene.crosshairPos[axis] * (total - 1)) + 1));
    setSlice({ current, total });
  }
  function fit(mode = modeRef.current, resetContrast = false) {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer.setPan2Dxyzmm([0, 0, 0, 1]);
    if (resetContrast) {
      viewer.setDefaults({ isRadiologicalConvention: true, crosshairWidth: crosshairVisible ? 1 : 0, isNearestInterpolation: true, multiplanarLayout: MULTIPLANAR_TYPE.GRID, multiplanarShowRender: SHOW_RENDER.ALWAYS, windowingGainFactor: 1 }, true);
      viewer.setMouseEventConfig({ leftButton: { primary: DRAG_MODE.crosshair }, rightButton: DRAG_MODE.windowing, centerButton: DRAG_MODE.pan });
      const type = { AXIAL: viewer.sliceTypeAxial, CORONAL: viewer.sliceTypeCoronal, SAGITTAL: viewer.sliceTypeSagittal, MULTIPLANAR: viewer.sliceTypeMultiplanar }[mode];
      viewer.setSliceType(type);
      viewer.setInterpolation(true); viewer.updateInterpolation(0, true);
      const maskIndex = maskIndexRef.current;
      if (maskIndex !== null) viewer.setOpacity(maskIndex, maskVisible ? maskOpacity / 100 : 0);
      syncWindowing(viewer.volumes[0]);
    }
    requestAnimationFrame(() => { viewer.resizeListener(); viewer.drawScene(); updateSlice(viewer, mode); });
  }
  function changeView(mode: ViewMode) {
    const viewer = viewerRef.current;
    if (!viewer) return;
    const type = { AXIAL: viewer.sliceTypeAxial, CORONAL: viewer.sliceTypeCoronal, SAGITTAL: viewer.sliceTypeSagittal, MULTIPLANAR: viewer.sliceTypeMultiplanar }[mode];
    if (mode === "MULTIPLANAR") {
      viewer.setMultiplanarLayout(MULTIPLANAR_TYPE.GRID);
      viewer.opts.multiplanarShowRender = SHOW_RENDER.ALWAYS;
      viewer.setMultiplanarPadPixels(4);
    }
    modeRef.current = mode; setViewMode(mode); viewer.setSliceType(type); fit(mode);
  }
  function moveToSlice(value: number) {
    const viewer = viewerRef.current;
    if (!viewer || viewMode === "MULTIPLANAR") return;
    const axis = viewMode === "AXIAL" ? 2 : viewMode === "CORONAL" ? 1 : 0;
    viewer.scene.crosshairPos[axis] = slice.total <= 1 ? 0.5 : (value - 1) / (slice.total - 1);
    viewer.drawScene(); updateSlice(viewer);
  }
  function toggleCrosshair() {
    const viewer = viewerRef.current;
    if (!viewer) return;
    const next = !crosshairVisible; viewer.setCrosshairWidth(next ? 1 : 0); setCrosshairVisible(next);
  }
  async function toggleFullscreen() {
    if (!shellRef.current) return;
    if (document.fullscreenElement) await document.exitFullscreen(); else await shellRef.current.requestFullscreen();
    requestAnimationFrame(() => viewerRef.current?.resizeListener());
  }

  useEffect(() => {
    let active = true; let attached = false;
    let updateWindowReadout: ((event: MouseEvent) => void) | null = null;
    const viewer = new Niivue({ show3Dcrosshair: true, backColor: [0, 0, 0, 1], isRadiologicalConvention: true, crosshairWidth: 1, isNearestInterpolation: true, multiplanarLayout: MULTIPLANAR_TYPE.GRID, multiplanarShowRender: SHOW_RENDER.ALWAYS, multiplanarPadPixels: 4, windowingGainFactor: 1 });
    viewer.setMouseEventConfig({ leftButton: { primary: DRAG_MODE.crosshair }, rightButton: DRAG_MODE.windowing, centerButton: DRAG_MODE.pan });
    viewerRef.current = viewer;
    async function load() {
      setMessage("NIfTI 영상을 불러오는 중입니다."); setAlignment(null); setHasMask(false); setMaskVisible(true); setSourceRole("");
      const manifest = await getNiftiViewerManifest(analysisId);
      const canvas = canvasRef.current;
      if (!active || !canvas) return;
      if (!canvas.getContext("webgl2")) return setMessage("WebGL2를 사용할 수 없습니다. 브라우저 하드웨어 가속을 확인해 주세요.");
      const source = manifest.inputs[0]; const mask = manifest.masks[0];
      if (!source) return setMessage("분석에 사용한 원본 NIfTI가 없습니다.");
      setSourceRole(source.role);
      await viewer.attachToCanvas(canvas); attached = true;
      if (!active) return;
      updateWindowReadout = (event: MouseEvent) => {
        if ((event.buttons & 2) === 0) return;
        requestAnimationFrame(() => syncWindowing(viewer.volumes[0]));
      };
      canvas.addEventListener("mousemove", updateWindowReadout);
      await viewer.loadVolumes([
        { ...authenticatedAsset(source.url), name: `${source.role.toLowerCase()}.nii.gz`, colormap: "gray", opacity: 1 },
        ...(mask ? [{ ...authenticatedAsset(mask.url), name: "ai-segmentation.nii.gz", colormap: "red", opacity: maskOpacity / 100 }] : []),
      ]);
      if (!active) return;
      const sourceGeometry = geometryOf(viewer.volumes[0]);
      const maskGeometry = viewer.volumes[1] ? geometryOf(viewer.volumes[1]) : undefined;
      const aligned = !maskGeometry || sameGeometry(sourceGeometry, maskGeometry);
      setAlignment(aligned); maskIndexRef.current = mask && aligned ? 1 : null; setHasMask(Boolean(mask && aligned));
      if (mask && !aligned) viewer.setOpacity(1, 0);
      viewer.setInterpolation(true); viewer.updateInterpolation(0, true); // linear source, nearest label mask
      modeRef.current = "AXIAL"; setViewMode("AXIAL"); viewer.setSliceType(viewer.sliceTypeAxial); viewer.setPan2Dxyzmm([0, 0, 0, 1]);
      viewer.onLocationChange = () => updateSlice(viewer);
      viewer.onIntensityChange = (volume) => syncWindowing(volume);
      syncWindowing(viewer.volumes[0]);
      requestAnimationFrame(() => { viewer.resizeListener(); viewer.drawScene(); updateSlice(viewer); });
      setMessage(mask && !aligned ? "마스크 shape·affine·spacing이 원본과 일치하지 않아 오버레이를 중지했습니다." : "");
    }
    load().catch((error: unknown) => { if (active) setMessage(`NIfTI를 불러오지 못했습니다. ${error instanceof Error ? error.message : String(error)}`); });
    return () => {
      active = false;
      const canvas = canvasRef.current;
      if (canvas && updateWindowReadout) canvas.removeEventListener("mousemove", updateWindowReadout);
      viewerRef.current = null; maskIndexRef.current = null;
      if (windowFrameRef.current !== null) cancelAnimationFrame(windowFrameRef.current);
      if (attached) try { viewer.closeDrawing(); } catch { /* canvas teardown */ }
    };
  }, [analysisId]);

  useEffect(() => { const viewer = viewerRef.current; const index = maskIndexRef.current; if (viewer && index !== null) viewer.setOpacity(index, maskVisible ? maskOpacity / 100 : 0); }, [maskOpacity, maskVisible]);
  useEffect(() => {
    const shell = shellRef.current; if (!shell || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => requestAnimationFrame(() => viewerRef.current?.resizeListener())); observer.observe(shell);
    return () => observer.disconnect();
  }, [message]);
  useEffect(() => {
    const viewer = viewerRef.current; const total = Number(viewer?.back?.dimsRAS?.[3] ?? 0);
    if (!viewer || !focusSlice || total < 1) return;
    modeRef.current = "AXIAL"; setViewMode("AXIAL"); viewer.setSliceType(viewer.sliceTypeAxial);
    viewer.scene.crosshairPos[2] = Math.min(1, Math.max(0, (focusSlice - 1) / Math.max(1, total - 1)));
    viewer.drawScene(); updateSlice(viewer, "AXIAL");
  }, [focusSlice]);
  useEffect(() => {
    const resize = () => requestAnimationFrame(() => viewerRef.current?.resizeListener());
    document.addEventListener("fullscreenchange", resize);
    return () => document.removeEventListener("fullscreenchange", resize);
  }, []);

  return <section ref={shellRef} className="ai-viewer-card nifti-result-viewer">
    <header className="nifti-toolbar">
      <div className="nifti-title"><span>NIFTI · NIIVUE</span><h3>{sourceRole ? `${sourceRole} 원본 + AI 분할` : "AI 분석 영상"}</h3></div>
      <div className="nifti-viewer-controls">
        <div className="nifti-viewer-modes">{MODES.map(([mode, label]) => <button type="button" key={mode} className={viewMode === mode ? "is-active" : ""} onClick={() => changeView(mode)}>{label}</button>)}</div>
        <button type="button" className={crosshairVisible ? "is-on" : ""} onClick={toggleCrosshair}>십자선</button>
        <output className="nifti-window-value" aria-label="현재 윈도우 레벨과 폭">WL {windowing ? windowing.level.toFixed(1) : "—"} · WW {windowing ? windowing.width.toFixed(1) : "—"}</output>
        <label><input type="checkbox" checked={maskVisible} disabled={!hasMask} onChange={(event) => setMaskVisible(event.target.checked)} /> 마스크</label>
        <label>투명도 <input type="range" min="0" max="100" value={maskOpacity} disabled={!hasMask} onChange={(event) => setMaskOpacity(Number(event.target.value))} /><strong>{maskOpacity}%</strong></label>
        <button type="button" onClick={() => fit()}>화면 맞춤</button><button type="button" onClick={() => fit(viewMode, true)}>초기화</button><button type="button" onClick={() => void toggleFullscreen()}>전체화면</button>
      </div>
    </header>
    <div className="nifti-viewer"><canvas ref={canvasRef} />{message && <div className={`nifti-viewer__message${alignment === false ? " is-warning" : ""}`}>{message}</div>}</div>
    <footer className="nifti-viewer-footer">
      <label className="nifti-slice-control"><span>슬라이스 {viewMode === "MULTIPLANAR" ? "다중" : `${slice.current} / ${slice.total}`}</span><input type="range" min="1" max={slice.total} value={slice.current} disabled={viewMode === "MULTIPLANAR"} onChange={(event) => moveToSlice(Number(event.target.value))} /></label>
      <span>휠: 슬라이스 · 가운데 드래그: 확대/이동 · 우클릭 드래그: WL/WW</span>
      {alignment !== null && <span className={alignment ? "is-aligned" : "is-misaligned"}>{alignment ? "원본·마스크 좌표 정합 확인" : "좌표 정합 불일치"}</span>}
    </footer>
  </section>;
}
