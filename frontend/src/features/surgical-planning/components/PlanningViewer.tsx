import { useRef } from "react";
import type { PlacedClip, ViewerMode } from "../types";

const TABS: Array<{ id: ViewerMode; label: string }> = [{ id: "AXIAL", label: "Axial" }, { id: "CORONAL", label: "Coronal" }, { id: "SAGITTAL", label: "Sagittal" }, { id: "VESSEL_3D", label: "3D Vessel" }];
interface Props { mode: ViewerMode; placedClips: PlacedClip[]; selectedClipInstanceId: string | null; onModeChange: (mode: ViewerMode) => void; onPlaceClip: (clipId: string, x: number, y: number) => void; onSelectClip: (id: string) => void; onMoveClip: (id: string, x: number, y: number) => void }
const clamp = (value: number) => Math.min(97, Math.max(3, value));

export default function PlanningViewer({ mode, placedClips, selectedClipInstanceId, onModeChange, onPlaceClip, onSelectClip, onMoveClip }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef<string | null>(null);
  const position = (x: number, y: number) => { const rect = viewportRef.current?.getBoundingClientRect(); return rect ? { x: clamp(((x - rect.left) / rect.width) * 100), y: clamp(((y - rect.top) / rect.height) * 100) } : null; };
  return <section className="clinical-card planning-viewer" aria-label="수술 플래닝 영상 뷰어">
    <div className="planning-viewer__heading"><div><span className="planning-eyebrow">MEDICAL IMAGING</span><h3>수술 · 시술 Planning Viewer</h3></div><span className="planning-viewer__mode-badge">2D MOCK VIEW</span></div>
    <div className="planning-view-tabs" role="tablist" aria-label="영상 방향">{TABS.map((tab) => <button className={mode === tab.id ? "is-active" : ""} key={tab.id} onClick={() => onModeChange(tab.id)} role="tab" aria-selected={mode === tab.id} type="button">{tab.label}</button>)}</div>
    <div className={`planning-viewport planning-viewport--${mode.toLowerCase()}`} ref={viewportRef}
      onDragOver={(event) => { if (mode === "VESSEL_3D") event.preventDefault(); }}
      onDrop={(event) => { if (mode !== "VESSEL_3D") return; event.preventDefault(); const clipId = event.dataTransfer.getData("application/x-braincdss-clip"); const next = position(event.clientX, event.clientY); if (clipId && next) onPlaceClip(clipId, next.x, next.y); }}
      onPointerMove={(event) => { if (!draggingRef.current) return; const next = position(event.clientX, event.clientY); if (next) onMoveClip(draggingRef.current, next.x, next.y); }}
      onPointerUp={() => { draggingRef.current = null; }} onPointerCancel={() => { draggingRef.current = null; }}>
      {mode === "VESSEL_3D" ? <>
        <div className="planning-vessel-placeholder" aria-hidden="true"><span className="planning-vessel-placeholder__stem"/><span className="planning-vessel-placeholder__branch planning-vessel-placeholder__branch--one"/><span className="planning-vessel-placeholder__branch planning-vessel-placeholder__branch--two"/><span className="planning-vessel-placeholder__branch planning-vessel-placeholder__branch--three"/></div>
        <p className="planning-viewport__hint">오른쪽 Virtual Clip을 이 영역으로 드래그하세요.</p>
        {placedClips.map((clip) => <button aria-label={`${clip.clipType} ${clip.size} 클립`} className={`placed-clip ${selectedClipInstanceId === clip.instanceId ? "is-selected" : ""}`} key={clip.instanceId} onClick={() => onSelectClip(clip.instanceId)} onPointerDown={(event) => { draggingRef.current = clip.instanceId; event.currentTarget.setPointerCapture(event.pointerId); onSelectClip(clip.instanceId); }} style={{ left: `${clip.position.x}%`, top: `${clip.position.y}%`, transform: `translate(-50%, -50%) rotate(${clip.rotation.z}deg)` }} type="button"><span/></button>)}
      </> : <div className="planning-viewport__empty"><strong>{TABS.find((tab) => tab.id === mode)?.label}</strong><span>의료 영상 연동 필요</span></div>}
    </div>
    <div className="planning-viewer__footer"><span>Viewer API 미연동</span><span>배치된 클립 {placedClips.length}개</span></div>
  </section>;
}
