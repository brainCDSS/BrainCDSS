import { useEffect, useMemo, useState } from "react";
import { getAIAnalysisResult } from "../ai-analysis/api";
import { getImagingStudy, getStudyAIAnalyses } from "../imaging/api";
import { getPatient } from "../patients/api";
import {
  confirmSurgicalPlan, createSurgicalPlan, createSurgicalPlanClip,
  createSurgicalPlanMessage, deleteSurgicalPlanClip, getSurgicalPlanMessages,
  getSurgicalPlans, saveSurgicalPlanDraft, updateSurgicalPlanClip,
} from "./api";
import CollaborationPanel from "./components/CollaborationPanel";
import PatientPlanningContext from "./components/PatientPlanningContext";
import PlanningControls from "./components/PlanningControls";
import PlanningViewer from "./components/PlanningViewer";
import { DEFAULT_CLIP_POSITION_Z, DEFAULT_CLIP_ROTATION, EMPTY_PLANNING_CASE, MOCK_TREATMENT_OPTIONS, MOCK_VIRTUAL_CLIPS } from "./mockData";
import type { CollaborationMessage, PlacedClip, PlanningPanelTab, SurgicalPlanApi, SurgicalPlanClipApi, ViewAttachment, ViewerMode } from "./types";
import "./surgical-planning.css";

const toPlacedClip = (clip: SurgicalPlanClipApi): PlacedClip => ({
  instanceId: clip.id, clipId: clip.clip_id,
  clipType: clip.clip_type === "CURVED" ? "CURVED" : "STANDARD", size: Number(clip.size),
  position: { x: Number(clip.position_x), y: Number(clip.position_y), z: Number(clip.position_z) },
  rotation: { x: Number(clip.rotation_x), y: Number(clip.rotation_y), z: Number(clip.rotation_z) },
});
const clipPayload = (clip: PlacedClip) => ({
  clip_id: clip.clipId, clip_type: clip.clipType, size: String(clip.size),
  position_x: String(clip.position.x), position_y: String(clip.position.y), position_z: String(clip.position.z),
  rotation_x: String(clip.rotation.x), rotation_y: String(clip.rotation.y), rotation_z: String(clip.rotation.z),
});

export default function SurgicalPlanningPage() {
  const query = useMemo(() => new URLSearchParams(globalThis.location?.search ?? ""), []);
  const patientId = query.get("patient_id"); const studyId = query.get("study_id"); const encounterId = query.get("encounter_id");
  const [analysisId, setAnalysisId] = useState<string | null>(null); const [plan, setPlan] = useState<SurgicalPlanApi | null>(null);
  const [planningCase, setPlanningCase] = useState(EMPTY_PLANNING_CASE); const [panelTab, setPanelTab] = useState<PlanningPanelTab>("planning"); const [viewerMode, setViewerMode] = useState<ViewerMode>("VESSEL_3D");
  const [placedClips, setPlacedClips] = useState<PlacedClip[]>([]); const [selectedClipInstanceId, setSelectedClipInstanceId] = useState<string | null>(null);
  const [treatment, setTreatment] = useState<string>(MOCK_TREATMENT_OPTIONS[2]); const [memo, setMemo] = useState(""); const [messages, setMessages] = useState<CollaborationMessage[]>([]);
  const [saving, setSaving] = useState(false); const [sending, setSending] = useState(false); const [error, setError] = useState<string | null>(null);
  const canEdit = Boolean(patientId && studyId) && plan?.status !== "CONFIRMED" && plan?.status !== "CANCELLED";
  const selectedClip = useMemo(() => placedClips.find((clip) => clip.instanceId === selectedClipInstanceId) ?? null, [placedClips, selectedClipInstanceId]);

  useEffect(() => {
    if (!patientId || !studyId) return;
    let active = true;
    Promise.all([getPatient(patientId), getImagingStudy(studyId), getStudyAIAnalyses(studyId), getSurgicalPlans({ patient_id: patientId, study_id: studyId })])
      .then(async ([patient, study, history, plans]) => {
        const latest = history.results[0]; const result = latest?.status === "COMPLETED" ? await getAIAnalysisResult(latest.analysis_id) : null;
        if (!active) return;
        setAnalysisId(latest?.analysis_id ?? null);
        setPlanningCase({
          patient: { name: patient.name, patientNo: patient.patient_no, sex: patient.sex ?? "제공 없음", age: patient.estimated_age == null ? "제공 없음" : String(patient.estimated_age) },
          examination: { diagnosis: "제공 없음", studyName: study.accession_number, studyDate: study.study_datetime },
          assignment: { department: "제공 없음", clinician: "제공 없음", status: study.status },
          aiSummary: { finding: result ? JSON.stringify(result.structured_findings) : "AI 결과 없음", confidence: result?.confidence == null ? "제공 없음" : String(result.confidence), lesionLocation: result && "laterality" in result.structured_findings ? String(result.structured_findings.laterality) : "제공 없음" },
        });
        const existing = plans.results[0] ?? null; setPlan(existing);
        if (existing) { setTreatment(existing.treatment_type); setMemo(existing.memo); setPlacedClips(existing.clips.map(toPlacedClip)); const response = await getSurgicalPlanMessages(existing.id); if (active) setMessages(response.results.map((item) => ({ id: item.id, sender: item.sender, message: item.message, createdAt: item.created_at, attachment: item.viewer_state as unknown as ViewAttachment }))); }
      }).catch(() => active && setError("플래닝 데이터를 불러오지 못했습니다."));
    return () => { active = false; };
  }, [patientId, studyId]);

  async function persistDraft() {
    if (!patientId || !studyId) throw new Error("환자와 영상검사를 먼저 선택하세요.");
    let current = plan;
    if (!current) current = await createSurgicalPlan({ patient_id: patientId, encounter_id: encounterId, study_id: studyId, ai_analysis_id: analysisId, treatment_type: treatment, memo });
    else current = await saveSurgicalPlanDraft(current.id, { version: current.version, treatment_type: treatment, memo });
    const persisted: PlacedClip[] = [];
    for (const clip of placedClips) {
      const response = clip.instanceId.startsWith("local-")
        ? await createSurgicalPlanClip(current.id, clipPayload(clip))
        : await updateSurgicalPlanClip(current.id, clip.instanceId, clipPayload(clip));
      persisted.push(toPlacedClip(response));
    }
    current = { ...current, clips: persisted.map((clip) => ({ ...clipPayload(clip), id: clip.instanceId, planning_id: current!.id, created_at: "", updated_at: "" })) };
    setPlan(current); setPlacedClips(persisted); return current;
  }
  async function save() { setSaving(true); setError(null); try { await persistDraft(); } catch { setError("플래닝 임시 저장에 실패했습니다."); } finally { setSaving(false); } }
  async function confirm() { setSaving(true); setError(null); try { const saved = await persistDraft(); setPlan(await confirmSurgicalPlan(saved.id, saved.version)); } catch { setError("플래닝 확정에 실패했습니다."); } finally { setSaving(false); } }
  const placeClip = (clipId: string, x: number, y: number) => { const source = MOCK_VIRTUAL_CLIPS.find((clip) => clip.id === clipId); if (!source || !canEdit) return; const instanceId = `local-${globalThis.crypto?.randomUUID?.() ?? Date.now()}`; setPlacedClips((current) => [...current, { instanceId, clipId: source.id, clipType: source.clipType, size: source.size, position: { x, y, z: DEFAULT_CLIP_POSITION_Z }, rotation: { ...DEFAULT_CLIP_ROTATION } }]); setSelectedClipInstanceId(instanceId); };
  async function removeClip(id: string) { setError(null); try { if (plan && !id.startsWith("local-")) await deleteSurgicalPlanClip(plan.id, id); setPlacedClips((current) => current.filter((clip) => clip.instanceId !== id)); setSelectedClipInstanceId(null); } catch { setError("클립 삭제에 실패했습니다."); } }
  async function sendMessage(message: string, attachment?: ViewAttachment) { if (!plan) return; setSending(true); setError(null); try { const saved = await createSurgicalPlanMessage(plan.id, { message, viewer_state: attachment ? { ...attachment } : {} }); setMessages((current) => [...current, { id: saved.id, sender: saved.sender, message: saved.message, createdAt: saved.created_at, attachment }]); } catch { setError("협업 메시지 전송에 실패했습니다."); throw new Error("message failed"); } finally { setSending(false); } }

  return <section className="clinical-page surgical-planning-page">
    <header className="clinical-page__heading surgical-planning-page__heading"><div><h2>수술 · 시술 플래닝</h2><p>영상 기반 치료 계획과 Virtual Clip 배치를 검토합니다.</p></div><span className="planning-mock-label">{plan ? plan.status : "저장 전"}</span></header>
    <div className="surgical-planning-layout"><PatientPlanningContext planningCase={planningCase}/><PlanningViewer mode={viewerMode} placedClips={placedClips} selectedClipInstanceId={selectedClipInstanceId} onModeChange={setViewerMode} onPlaceClip={placeClip} onSelectClip={setSelectedClipInstanceId} onMoveClip={(id, x, y) => canEdit && setPlacedClips((current) => current.map((clip) => clip.instanceId === id ? { ...clip, position: { ...clip.position, x, y } } : clip))}/><aside className="clinical-card planning-side-panel">
      <div className="planning-panel-tabs" role="tablist" aria-label="플래닝 패널"><button className={panelTab === "planning" ? "is-active" : ""} onClick={() => setPanelTab("planning")} role="tab" aria-selected={panelTab === "planning"} type="button">플래닝</button><button className={panelTab === "collaboration" ? "is-active" : ""} onClick={() => setPanelTab("collaboration")} role="tab" aria-selected={panelTab === "collaboration"} type="button">협업 메시지</button></div>
      {panelTab === "planning" ? <PlanningControls planningCase={planningCase} clips={MOCK_VIRTUAL_CLIPS} selectedClip={selectedClip} treatment={treatment} memo={memo} saving={saving} canEdit={canEdit} error={error} onTreatmentChange={setTreatment} onMemoChange={setMemo} onClipChange={(changed) => setPlacedClips((current) => current.map((clip) => clip.instanceId === changed.instanceId ? changed : clip))} onDeleteClip={(id) => void removeClip(id)} onSave={() => void save()} onConfirm={() => void confirm()}/> : <CollaborationPanel messages={messages} viewerMode={viewerMode} selectedClipInstanceId={selectedClipInstanceId} placedClipCount={placedClips.length} sending={sending} enabled={Boolean(plan)} onSend={sendMessage}/>} 
    </aside></div>
  </section>;
}
