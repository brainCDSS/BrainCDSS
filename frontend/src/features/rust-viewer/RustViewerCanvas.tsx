import { useEffect, useRef, useState } from "react";
import { cmapper } from "@niivue/niivue";
import type { LoadedViewer, RenderSettings } from "./types";

const TURBO = new Uint8Array(cmapper.colormap("turbo"));
export interface RenderMetrics { wasmMs: number; imageDataMs: number; canvasMs: number; totalMs: number }
interface Props { loaded: LoadedViewer; settings: RenderSettings; onSlice: (index: number) => void; onError: (message: string) => void; onMetrics?: (metrics: RenderMetrics) => void }

export default function RustViewerCanvas({ loaded, settings, onSlice, onError, onMetrics }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const planeRef = useRef<HTMLCanvasElement | null>(null);
  const drag = useRef<{ x: number; y: number } | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const [width, height] = loaded.source.dimensions;
    let frame = 0;
    const draw = () => {
      try {
        const totalStart = performance.now();
        const context = canvas.getContext("2d");
        if (!context) throw new Error("Canvas 2D를 사용할 수 없습니다.");
        const wasmStart = performance.now();
        const rgba = loaded.engine.render_slice(settings.slice, settings.window, settings.level, settings.maskOpacity, settings.probabilityOpacity, TURBO);
        const wasmEnd = performance.now();
        const plane = planeRef.current ?? document.createElement("canvas");
        planeRef.current = plane;
        if (plane.width !== width) plane.width = width;
        if (plane.height !== height) plane.height = height;
        const planeContext = plane.getContext("2d");
        if (!planeContext) throw new Error("영상 버퍼를 그릴 수 없습니다.");
        const clamped = new Uint8ClampedArray(rgba.buffer as ArrayBuffer, rgba.byteOffset, rgba.byteLength);
        planeContext.putImageData(new ImageData(clamped, width, height), 0, 0);
        const imageDataEnd = performance.now();
        const rect = canvas.getBoundingClientRect(); const ratio = window.devicePixelRatio || 1;
        const canvasWidth = Math.round(rect.width * ratio), canvasHeight = Math.round(rect.height * ratio);
        if (canvas.width !== canvasWidth) canvas.width = canvasWidth;
        if (canvas.height !== canvasHeight) canvas.height = canvasHeight;
        const physicalWidth = width * loaded.source.spacing[0], physicalHeight = height * loaded.source.spacing[1];
        const fit = Math.min(canvas.width / physicalWidth, canvas.height / physicalHeight) * .94 * zoom;
        context.fillStyle = "#05080d"; context.fillRect(0, 0, canvas.width, canvas.height);
        context.save(); context.translate(canvas.width / 2 + pan.x * ratio, canvas.height / 2 + pan.y * ratio);
        context.scale(-1, -1); context.imageSmoothingEnabled = false;
        context.drawImage(plane, -physicalWidth * fit / 2, -physicalHeight * fit / 2, physicalWidth * fit, physicalHeight * fit);
        context.restore();
        const canvasEnd = performance.now();
        onMetrics?.({ wasmMs: wasmEnd - wasmStart, imageDataMs: imageDataEnd - wasmEnd, canvasMs: canvasEnd - imageDataEnd, totalMs: canvasEnd - totalStart });
      } catch { onError("Rust 슬라이스 렌더링에 실패했습니다. 기존 Viewer로 전환할 수 있습니다."); }
    };
    const scheduleDraw = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(draw); };
    scheduleDraw(); const observer = new ResizeObserver(scheduleDraw); observer.observe(canvas);
    return () => { observer.disconnect(); cancelAnimationFrame(frame); };
  }, [loaded, settings, zoom, pan, onError, onMetrics]);

  return <div className="rust-canvas-stage"><canvas ref={canvasRef} aria-label="Rust axial 영상" onWheel={(event) => { event.preventDefault(); onSlice(Math.max(0, Math.min(loaded.source.dimensions[2] - 1, settings.slice + Math.sign(event.deltaY)))); }}
    onPointerDown={(event) => { drag.current = { x: event.clientX, y: event.clientY }; event.currentTarget.setPointerCapture(event.pointerId); }}
    onPointerMove={(event) => { if (!drag.current) return; const dx = event.clientX - drag.current.x, dy = event.clientY - drag.current.y; setPan((value) => ({ x: value.x + dx, y: value.y + dy })); drag.current = { x: event.clientX, y: event.clientY }; }}
    onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }} />
    <span className="rust-direction rust-direction-left">R</span><span className="rust-direction rust-direction-right">L</span><span className="rust-direction rust-direction-top">A</span><span className="rust-direction rust-direction-bottom">P</span>
    <div className="rust-zoom-controls"><button type="button" onClick={() => setZoom((value) => Math.max(.25, value / 1.2))}>−</button><output>Zoom {Math.round(zoom * 100)}%</output><button type="button" onClick={() => setZoom((value) => Math.min(8, value * 1.2))}>+</button><button type="button" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}>화면 맞춤</button></div></div>;
}
