import { useMemo, useState } from "react";
import CollaborationPanel from "./components/CollaborationPanel";
import PatientPlanningContext from "./components/PatientPlanningContext";
import PlanningControls from "./components/PlanningControls";
import PlanningViewer from "./components/PlanningViewer";
import { DEFAULT_CLIP_POSITION_Z, DEFAULT_CLIP_ROTATION, MOCK_CURRENT_USER, MOCK_INITIAL_MESSAGES, MOCK_PLANNING_CASE, MOCK_TREATMENT_OPTIONS, MOCK_VIRTUAL_CLIPS } from "./mockData";
import type { CollaborationMessage, PlacedClip, PlanningPanelTab, ViewerMode } from "./types";
import "./surgical-planning.css";

export default function SurgicalPlanningPage() {
  const [panelTab, setPanelTab] = useState<PlanningPanelTab>("planning"); const [viewerMode, setViewerMode] = useState<ViewerMode>("VESSEL_3D");
  const [placedClips, setPlacedClips] = useState<PlacedClip[]>([]); const [selectedClipInstanceId, setSelectedClipInstanceId] = useState<string | null>(null);
  const [treatment, setTreatment] = useState<string>(MOCK_TREATMENT_OPTIONS[2]); const [memo, setMemo] = useState(""); const [messages, setMessages] = useState<CollaborationMessage[]>(MOCK_INITIAL_MESSAGES);
  const selectedClip = useMemo(() => placedClips.find((clip) => clip.instanceId === selectedClipInstanceId) ?? null, [placedClips, selectedClipInstanceId]);
  const placeClip = (clipId: string, x: number, y: number) => { const source = MOCK_VIRTUAL_CLIPS.find((clip) => clip.id === clipId); if (!source) return; const instanceId = globalThis.crypto?.randomUUID?.() ?? `placed-clip-${Date.now()}`; setPlacedClips((current) => [...current, { instanceId, clipId: source.id, clipType: source.clipType, size: source.size, position: { x, y, z: DEFAULT_CLIP_POSITION_Z }, rotation: { ...DEFAULT_CLIP_ROTATION } }]); setSelectedClipInstanceId(instanceId); };
  return <section className="clinical-page surgical-planning-page">
    <header className="clinical-page__heading surgical-planning-page__heading"><div><h2>수술 · 시술 플래닝</h2><p>영상 기반 치료 계획과 Virtual Clip 배치를 검토합니다.</p></div><span className="planning-mock-label">MOCK WORKSPACE · API 연동 필요</span></header>
    <div className="surgical-planning-layout">
      <PatientPlanningContext planningCase={MOCK_PLANNING_CASE}/>
      <PlanningViewer mode={viewerMode} placedClips={placedClips} selectedClipInstanceId={selectedClipInstanceId} onModeChange={setViewerMode} onPlaceClip={placeClip} onSelectClip={setSelectedClipInstanceId} onMoveClip={(id, x, y) => setPlacedClips((current) => current.map((clip) => clip.instanceId === id ? { ...clip, position: { ...clip.position, x, y } } : clip))}/>
      <aside className="clinical-card planning-side-panel">
        <div className="planning-panel-tabs" role="tablist" aria-label="플래닝 패널"><button className={panelTab === "planning" ? "is-active" : ""} onClick={() => setPanelTab("planning")} role="tab" aria-selected={panelTab === "planning"} type="button">Planning</button><button className={panelTab === "collaboration" ? "is-active" : ""} onClick={() => setPanelTab("collaboration")} role="tab" aria-selected={panelTab === "collaboration"} type="button">Realtime Collaboration</button></div>
        {panelTab === "planning" ? <PlanningControls planningCase={MOCK_PLANNING_CASE} clips={MOCK_VIRTUAL_CLIPS} selectedClip={selectedClip} treatment={treatment} memo={memo} onTreatmentChange={setTreatment} onMemoChange={setMemo} onClipChange={(changed) => setPlacedClips((current) => current.map((clip) => clip.instanceId === changed.instanceId ? changed : clip))} onDeleteClip={(id) => { setPlacedClips((current) => current.filter((clip) => clip.instanceId !== id)); setSelectedClipInstanceId(null); }}/> : <CollaborationPanel currentUser={MOCK_CURRENT_USER} messages={messages} viewerMode={viewerMode} selectedClipInstanceId={selectedClipInstanceId} placedClipCount={placedClips.length} onSend={(message) => setMessages((current) => [...current, message])}/>} 
      </aside>
    </div>
  </section>;
}
