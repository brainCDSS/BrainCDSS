import { useEffect, useRef, useState } from "react";
import { DRAG_MODE, MULTIPLANAR_TYPE, Niivue, SHOW_RENDER } from "@niivue/niivue";
import { authenticatedAsset } from "../../api/client";
import { getNiftiViewerManifest } from "./api";
import type { NiftiProbe } from "./types";

type ViewMode = "AXIAL" | "CORONAL" | "SAGITTAL" | "MULTIPLANAR";
type Geometry = { shape: number[]; spacing: number[]; affine: number[] };
type ViewerState = { crosshair: [number, number, number]; pan: [number, number, number, number]; mode: ViewMode };
const MODES: Array<[ViewMode, string]> = [["AXIAL", "축상"], ["CORONAL", "관상"], ["SAGITTAL", "시상"], ["MULTIPLANAR", "멀티뷰"]];

function geometryOf(volume: Niivue["volumes"][number]): Geometry {
  return { shape: Array.from(volume.dimsRAS?.slice(1, 4) ?? []), spacing: Array.from(volume.pixDimsRAS?.slice(1, 4) ?? []), affine: Array.from(volume.matRAS ?? []) };
}
function sameGeometry(left: Geometry, right: Geometry) {
  const close = (a: number[], b: number[], tolerance: number) => a.length === b.length && a.every((value, index) => Math.abs(value - b[index]) <= tolerance);
  return close(left.shape, right.shape, 0) && close(left.spacing, right.spacing, 0.001) && close(left.affine, right.affine, 0.001);
}

function xaiPercentileWindow(volume: Niivue["volumes"][number]): [number, number] | null {
  const values = Array.from((volume.img as unknown as ArrayLike<number>) ?? [])
    .filter((value) => Number.isFinite(value) && value !== 0)
    .sort((left, right) => left - right);
  if (values.length < 2) return null;
  const valueAt = (percentile: number) => values[Math.min(values.length - 1, Math.max(0, Math.round((values.length - 1) * percentile)))];
  const minimum = valueAt(0.9); const maximum = valueAt(0.995);
  return maximum > minimum ? [minimum, maximum] : null;
}

function readVoxel(volume: Niivue["volumes"][number] | undefined, voxel: [number, number, number]): number | null {
  if (!volume?.dimsRAS) return null;
  const image = volume.img as unknown as ArrayLike<number> | undefined;
  if (!image) return null;
  const [x, y, z] = voxel; const width = Number(volume.dimsRAS[1]); const height = Number(volume.dimsRAS[2]);
  if (x < 0 || y < 0 || z < 0 || x >= width || y >= height || z >= Number(volume.dimsRAS[3])) return null;
  const value = Number(image[x + y * width + z * width * height]);
  return Number.isFinite(value) ? value : null;
}

export default function NiftiViewer({ analysisId, focusSlice, onProbe }: { analysisId: string; focusSlice?: number | null; onProbe?: (probe: NiftiProbe | null) => void }) {
  const shellRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewerRef = useRef<Niivue | null>(null);
  const probabilityIndexRef = useRef<number | null>(null);
  const maskIndexRef = useRef<number | null>(null);
  const xaiIndexRef = useRef<number | null>(null);
  const modeRef = useRef<ViewMode>("AXIAL");
  const windowFrameRef = useRef<number | null>(null);
  const retainedViewerStateRef = useRef<ViewerState | null>(null);
  const componentIndexRef = useRef<number | null>(null);
  const [message, setMessage] = useState("NIfTI 영상을 불러오는 중입니다.");
  const [sourceRole, setSourceRole] = useState("");
  const [sourceRoles, setSourceRoles] = useState<string[]>([]);
  const [selectedSourceRole, setSelectedSourceRole] = useState("");
  const [hasMask, setHasMask] = useState(false);
  const [maskVisible, setMaskVisible] = useState(true);
  const [maskOpacity, setMaskOpacity] = useState(72);
  const [hasProbability, setHasProbability] = useState(false);
  const [probabilityVisible, setProbabilityVisible] = useState(false);
  const [probabilityOpacity, setProbabilityOpacity] = useState(48);
  const [hasXai, setHasXai] = useState(false);
  const [xaiVisible, setXaiVisible] = useState(false);
  const [xaiOpacity, setXaiOpacity] = useState(45);
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

  function setSourceWindow(level: number, width: number) {
    const viewer = viewerRef.current;
    const source = viewer?.volumes[0];
    if (!viewer || !source) return;
    source.cal_min = level - width / 2;
    source.cal_max = level + width / 2;
    viewer.updateGLVolume();
    viewer.drawScene();
    syncWindowing(source);
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
      const probabilityIndex = probabilityIndexRef.current;
      if (probabilityIndex !== null) viewer.setOpacity(probabilityIndex, probabilityVisible ? probabilityOpacity / 100 : 0);
      const xaiIndex = xaiIndexRef.current;
      if (xaiIndex !== null) viewer.setOpacity(xaiIndex, xaiVisible ? xaiOpacity / 100 : 0);
      if (viewer.volumes[0]?.name.toLowerCase().startsWith("ct")) setSourceWindow(40, 80);
      else syncWindowing(viewer.volumes[0]);
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
      setMessage("NIfTI 영상을 불러오는 중입니다."); setAlignment(null); setHasMask(false); setMaskVisible(true); setHasProbability(false); setProbabilityVisible(false); setHasXai(false); setXaiVisible(false); setSourceRole("");
      const manifest = await getNiftiViewerManifest(analysisId);
      const canvas = canvasRef.current;
      if (!active || !canvas) return;
      if (!canvas.getContext("webgl2")) return setMessage("WebGL2를 사용할 수 없습니다. 브라우저 하드웨어 가속을 확인해 주세요.");
      const roles = manifest.inputs.map((item) => item.role);
      const defaultRole = roles.includes("DWI") ? "DWI" : roles[0];
      const activeRole = selectedSourceRole || defaultRole;
      const source = manifest.inputs.find((item) => item.role === activeRole);
      const probability = manifest.probabilities?.[0]; const mask = manifest.masks[0]; const components = manifest.components?.[0];
      const xai = manifest.xai?.find((item) => item.role === activeRole) ?? manifest.xai?.find((item) => !item.role);
      if (!source) return setMessage("분석에 사용한 원본 NIfTI가 없습니다.");
      setSourceRole(source.role); setSourceRoles(roles);
      if (!selectedSourceRole) setSelectedSourceRole(defaultRole);
      await viewer.attachToCanvas(canvas); attached = true;
      if (!active) return;
      updateWindowReadout = (event: MouseEvent) => {
        if ((event.buttons & 2) === 0) return;
        requestAnimationFrame(() => syncWindowing(viewer.volumes[0]));
      };
      canvas.addEventListener("mousemove", updateWindowReadout);
      await viewer.loadVolumes([
        { ...authenticatedAsset(source.url), name: `${source.role.toLowerCase()}.nii.gz`, colormap: "gray", opacity: 1 },
        ...(probability ? [{ ...authenticatedAsset(probability.url), name: "lesion-probability.nii.gz", colormap: "turbo", opacity: 0, cal_min: 0.15, cal_max: 1, trustCalMinMax: true, ignoreZeroVoxels: true }] : []),
        ...(mask ? [{ ...authenticatedAsset(mask.url), name: "ai-segmentation.nii.gz", colormap: "red", opacity: maskOpacity / 100, cal_min: 0.5, trustCalMinMax: true, ignoreZeroVoxels: true }] : []),
        ...(components ? [{ ...authenticatedAsset(components.url), name: "lesion-components.nii.gz", colormap: "gray", opacity: 0, trustCalMinMax: true, ignoreZeroVoxels: true }] : []),
        ...(xai ? [{
          ...authenticatedAsset(xai.url),
          name: "integrated-gradients.nii.gz",
          // XAI importance increases from red to yellow/white. This keeps the
          // lesion-localized heatmap visually distinct from the red mask.
          colormap: "hot",
          opacity: 0,
          trustCalMinMax: true,
          ignoreZeroVoxels: true,
          // Grad-CAM is normalized to 0..1. Hide background activation instead
          // of rendering the low end of the color map as an opaque dark layer.
        }] : []),
      ]);
      if (!active) return;
      const sourceGeometry = geometryOf(viewer.volumes[0]);
      let nextVolumeIndex = 1;
      const probabilityIndex = probability ? nextVolumeIndex++ : null;
      const maskIndex = mask ? nextVolumeIndex++ : null;
      const componentIndex = components ? nextVolumeIndex++ : null;
      const xaiIndex = xai ? nextVolumeIndex++ : null;
      const probabilityGeometry = probabilityIndex === null ? undefined : geometryOf(viewer.volumes[probabilityIndex]);
      const probabilityAligned = !probabilityGeometry || sameGeometry(sourceGeometry, probabilityGeometry);
      probabilityIndexRef.current = probabilityIndex !== null && probabilityAligned ? probabilityIndex : null;
      setHasProbability(probabilityIndex !== null && probabilityAligned);
      setProbabilityVisible(false);
      if (probabilityIndex !== null) {
        const probabilityVolume = viewer.volumes[probabilityIndex];
        probabilityVolume.cal_min = 0.15;
        probabilityVolume.cal_max = 1;
        probabilityVolume.colormapType = 1;
        viewer.setOpacity(probabilityIndex, 0);
      }
      const maskGeometry = maskIndex === null ? undefined : geometryOf(viewer.volumes[maskIndex]);
      const aligned = !maskGeometry || sameGeometry(sourceGeometry, maskGeometry);
      setAlignment(aligned && probabilityAligned); maskIndexRef.current = maskIndex !== null && aligned ? maskIndex : null; setHasMask(maskIndex !== null && aligned);
      if (maskIndex !== null) {
        const maskVolume = viewer.volumes[maskIndex];
        // Binary labels must start at the visible end of the red LUT. Without
        // this window a label value of 1 can be rendered as near-black.
        maskVolume.cal_min = 0.5;
        maskVolume.cal_max = Math.max(1, Number(maskVolume.cal_max) || 1);
        maskVolume.colormapType = 1;
        viewer.updateGLVolume();
      }
      if (maskIndex !== null && !aligned) viewer.setOpacity(maskIndex, 0);
      if (probabilityIndex !== null && !probabilityAligned) viewer.setOpacity(probabilityIndex, 0);
      const componentGeometry = componentIndex === null ? undefined : geometryOf(viewer.volumes[componentIndex]);
      const componentAligned = !componentGeometry || sameGeometry(sourceGeometry, componentGeometry);
      componentIndexRef.current = componentIndex !== null && componentAligned ? componentIndex : null;
      if (componentIndex !== null) viewer.setOpacity(componentIndex, 0);
      const xaiGeometry = xaiIndex === null ? undefined : geometryOf(viewer.volumes[xaiIndex]);
      const xaiAligned = !xaiGeometry || sameGeometry(sourceGeometry, xaiGeometry);
      xaiIndexRef.current = xaiIndex !== null && xaiAligned ? xaiIndex : null;
      setHasXai(xaiIndex !== null && xaiAligned); setXaiVisible(false);
      if (xaiIndex !== null) {
        const xaiVolume = viewer.volumes[xaiIndex];
        const percentile = xaiPercentileWindow(xaiVolume);
        if (percentile) { xaiVolume.cal_min = percentile[0]; xaiVolume.cal_max = percentile[1]; }
        xaiVolume.colormapType = 1; // transparent below cal_min
        // Keep the heatmap above both the anatomical image and segmentation.
        viewer.moveVolumeToTop(xaiVolume);
        viewer.updateGLVolume();
        viewer.setOpacity(xaiIndex, 0);
      }
      viewer.setInterpolation(true); viewer.updateInterpolation(0, true); // linear source, nearest label mask
      // Use the conventional non-contrast brain CT display window on first open.
      if (source.role === "CT") setSourceWindow(40, 80);
      const retained = retainedViewerStateRef.current;
      const restoredMode = retained?.mode ?? "AXIAL";
      modeRef.current = restoredMode; setViewMode(restoredMode);
      viewer.setSliceType({ AXIAL: viewer.sliceTypeAxial, CORONAL: viewer.sliceTypeCoronal, SAGITTAL: viewer.sliceTypeSagittal, MULTIPLANAR: viewer.sliceTypeMultiplanar }[restoredMode]);
      viewer.scene.crosshairPos = retained?.crosshair ?? [0.5, 0.5, 0.5];
      viewer.setPan2Dxyzmm(retained?.pan ?? [0, 0, 0, 1]);
      retainedViewerStateRef.current = null;
      const emitProbe = () => {
        const dimensions = viewer.volumes[0]?.dimsRAS;
        if (!dimensions) return;
        const voxel = [0, 1, 2].map((axis) => Math.round(viewer.scene.crosshairPos[axis] * (Number(dimensions[axis + 1]) - 1))) as [number, number, number];
        const componentValue = readVoxel(componentIndex === null ? undefined : viewer.volumes[componentIndex], voxel);
        onProbe?.({ voxel, slice: Math.round(viewer.scene.crosshairPos[2] * (Number(dimensions[3]) - 1)) + 1, sourceRole: source.role, sourceValue: readVoxel(viewer.volumes[0], voxel), probability: readVoxel(probabilityIndex === null ? undefined : viewer.volumes[probabilityIndex], voxel), maskValue: readVoxel(maskIndex === null ? undefined : viewer.volumes[maskIndex], voxel), xaiValue: readVoxel(xaiIndex === null ? undefined : viewer.volumes[xaiIndex], voxel), componentId: componentValue == null ? null : Math.round(componentValue) });
      };
      viewer.onLocationChange = () => { updateSlice(viewer); };
      canvas.addEventListener("click", emitProbe);
      viewer.onIntensityChange = (volume) => syncWindowing(volume);
      syncWindowing(viewer.volumes[0]);
      requestAnimationFrame(() => { viewer.resizeListener(); viewer.drawScene(); updateSlice(viewer); });
      setMessage((mask && !aligned) || (probability && !probabilityAligned) ? "마스크 또는 병변 가능도 지도의 shape·affine·spacing이 원본과 일치하지 않아 오버레이를 중지했습니다." : "");
    }
    load().catch((error: unknown) => { if (active) setMessage(`NIfTI를 불러오지 못했습니다. ${error instanceof Error ? error.message : String(error)}`); });
    return () => {
      active = false;
      const canvas = canvasRef.current;
      if (canvas && updateWindowReadout) canvas.removeEventListener("mousemove", updateWindowReadout);
      onProbe?.(null);
      viewerRef.current = null; probabilityIndexRef.current = null; maskIndexRef.current = null; componentIndexRef.current = null; xaiIndexRef.current = null;
      if (windowFrameRef.current !== null) cancelAnimationFrame(windowFrameRef.current);
      if (attached) try { viewer.closeDrawing(); } catch { /* canvas teardown */ }
    };
  }, [analysisId, selectedSourceRole]);

  useEffect(() => { const viewer = viewerRef.current; const index = maskIndexRef.current; if (viewer && index !== null) viewer.setOpacity(index, maskVisible ? maskOpacity / 100 : 0); }, [maskOpacity, maskVisible]);
  useEffect(() => { const viewer = viewerRef.current; const index = probabilityIndexRef.current; if (viewer && index !== null) viewer.setOpacity(index, probabilityVisible ? probabilityOpacity / 100 : 0); }, [probabilityOpacity, probabilityVisible]);
  useEffect(() => { const viewer = viewerRef.current; const index = xaiIndexRef.current; if (viewer && index !== null) viewer.setOpacity(index, xaiVisible ? xaiOpacity / 100 : 0); }, [xaiOpacity, xaiVisible]);
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
      <div className="nifti-title"><h3>{sourceRole === "DWI" || sourceRole === "ADC" ? `MRI · ${sourceRole}` : sourceRole ? `${sourceRole} 영상` : "AI 분석 영상"}</h3></div>
      <div className="nifti-viewer-controls">
        <div className="nifti-primary-controls">
        {sourceRoles.length > 1 && <div className="nifti-source-selector" aria-label="MRI 영상 선택">{sourceRoles.map((role) => <button type="button" key={role} className={sourceRole === role ? "is-active" : ""} onClick={() => { const viewer = viewerRef.current; if (viewer) retainedViewerStateRef.current = { crosshair: [...viewer.scene.crosshairPos] as [number, number, number], pan: [...viewer.scene.pan2Dxyzmm] as [number, number, number, number], mode: modeRef.current }; setSelectedSourceRole(role); }}>{role}</button>)}</div>}
        <div className="nifti-viewer-modes">{MODES.map(([mode, label]) => <button type="button" key={mode} className={viewMode === mode ? "is-active" : ""} onClick={() => changeView(mode)}>{label}</button>)}</div>
        <button type="button" className={crosshairVisible ? "is-on" : ""} onClick={toggleCrosshair}>십자선</button>
        <output className="nifti-window-value" aria-label="현재 윈도우 레벨과 폭">WL {windowing ? windowing.level.toFixed(1) : "—"} · WW {windowing ? windowing.width.toFixed(1) : "—"}</output>
        {sourceRole === "CT" && <><button type="button" onClick={() => setSourceWindow(40, 80)}>뇌창</button><button type="button" onClick={() => setSourceWindow(600, 2800)}>뼈창</button></>}
        </div>
        <div className="nifti-overlay-controls">
        <label><input type="checkbox" checked={maskVisible} disabled={!hasMask} onChange={(event) => setMaskVisible(event.target.checked)} /> 마스크</label>
        <label>투명도 <input type="range" min="0" max="100" value={maskOpacity} disabled={!hasMask} onChange={(event) => setMaskOpacity(Number(event.target.value))} /><strong>{maskOpacity}%</strong></label>
        <label><input type="checkbox" checked={probabilityVisible} disabled={!hasProbability} onChange={(event) => setProbabilityVisible(event.target.checked)} /> 병변 가능도</label>
        <label>가능도 <input type="range" min="0" max="100" value={probabilityOpacity} disabled={!hasProbability} onChange={(event) => setProbabilityOpacity(Number(event.target.value))} /><strong>{probabilityOpacity}%</strong></label>
        <label title="Smooth Integrated Gradients"><input type="checkbox" checked={xaiVisible} disabled={!hasXai} onChange={(event) => setXaiVisible(event.target.checked)} /> XAI</label>
        <label>XAI <input type="range" min="0" max="100" value={xaiOpacity} disabled={!hasXai} onChange={(event) => setXaiOpacity(Number(event.target.value))} /><strong>{xaiOpacity}%</strong></label>
        </div>
        <div className="nifti-view-actions">
        <button type="button" onClick={() => fit()}>화면 맞춤</button><button type="button" onClick={() => fit(viewMode, true)}>초기화</button><button type="button" onClick={() => void toggleFullscreen()}>전체화면</button>
        </div>
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
