import { MOCK_TREATMENT_OPTIONS } from "../mockData";
import type { PlacedClip, PlanningCase, VirtualClip } from "../types";

interface Props {
  planningCase: PlanningCase; clips: VirtualClip[]; selectedClip: PlacedClip | null;
  treatment: string; memo: string; saving: boolean; canEdit: boolean; error: string | null;
  onTreatmentChange: (value: string) => void; onMemoChange: (value: string) => void;
  onClipChange: (clip: PlacedClip) => void; onDeleteClip: (id: string) => void;
  onSave: () => void; onConfirm: () => void;
}
function NumberField({ label, value, onChange, disabled }: { label: string; value: number; onChange: (value: number) => void; disabled: boolean }) { return <label className="clip-number-field"><span>{label}</span><input type="number" value={value} disabled={disabled} onChange={(event) => onChange(Number(event.target.value))}/></label>; }
export default function PlanningControls({ planningCase, clips, selectedClip, treatment, memo, saving, canEdit, error, onTreatmentChange, onMemoChange, onClipChange, onDeleteClip, onSave, onConfirm }: Props) {
  const position = (axis: "x" | "y" | "z", value: number) => selectedClip && onClipChange({ ...selectedClip, position: { ...selectedClip.position, [axis]: value } });
  const rotation = (axis: "x" | "y" | "z", value: number) => selectedClip && onClipChange({ ...selectedClip, rotation: { ...selectedClip.rotation, [axis]: value } });
  return <div className="planning-controls"><div className="planning-controls__scroll">
    <section className="planning-control-section"><h4>AI 분석 요약</h4><dl className="planning-ai-summary"><div><dt>소견</dt><dd>{planningCase.aiSummary.finding}</dd></div><div><dt>신뢰도</dt><dd>{planningCase.aiSummary.confidence}</dd></div><div><dt>병변 위치</dt><dd>{planningCase.aiSummary.lesionLocation}</dd></div></dl></section>
    <section className="planning-control-section"><label className="clinical-field"><span>치료 방법</span><select value={treatment} disabled={!canEdit} onChange={(event) => onTreatmentChange(event.target.value)}>{MOCK_TREATMENT_OPTIONS.map((option) => <option key={option}>{option}</option>)}</select></label></section>
    <section className="planning-control-section"><h4>Virtual Clip Library <small>정적 카탈로그</small></h4><div className="virtual-clip-library">{clips.map((clip) => <button draggable={canEdit} key={clip.id} onDragStart={(event) => { event.dataTransfer.effectAllowed = "copy"; event.dataTransfer.setData("application/x-braincdss-clip", clip.id); }} type="button"><span className={`virtual-clip-icon virtual-clip-icon--${clip.clipType.toLowerCase()}`}/><strong>{clip.name}</strong><small>{clip.clipType} · {clip.size} mm</small></button>)}</div></section>
    <section className="planning-control-section"><h4>Clip 속성</h4>{selectedClip ? <><div className="clip-property-grid"><NumberField label="X" value={selectedClip.position.x} disabled={!canEdit} onChange={(v) => position("x", v)}/><NumberField label="Y" value={selectedClip.position.y} disabled={!canEdit} onChange={(v) => position("y", v)}/><NumberField label="Z" value={selectedClip.position.z} disabled={!canEdit} onChange={(v) => position("z", v)}/></div><div className="clip-property-grid"><NumberField label="Rx" value={selectedClip.rotation.x} disabled={!canEdit} onChange={(v) => rotation("x", v)}/><NumberField label="Ry" value={selectedClip.rotation.y} disabled={!canEdit} onChange={(v) => rotation("y", v)}/><NumberField label="Rz" value={selectedClip.rotation.z} disabled={!canEdit} onChange={(v) => rotation("z", v)}/></div><button className="planning-delete-button" disabled={!canEdit} onClick={() => onDeleteClip(selectedClip.instanceId)} type="button">선택 클립 삭제</button></> : <p className="planning-compact-state">3D Viewer에 클립을 배치하거나 선택하세요.</p>}</section>
    <section className="planning-control-section"><label className="clinical-field"><span>플래닝 메모</span><textarea value={memo} disabled={!canEdit} onChange={(event) => onMemoChange(event.target.value)} placeholder="플래닝 메모를 입력하세요."/></label></section>
    {error && <p className="planning-compact-state" role="alert">{error}</p>}
    </div><div className="clinical-action-bar planning-actions"><button className="clinical-action" disabled={saving || !canEdit} onClick={onSave} type="button">{saving ? "저장 중..." : "임시 저장"}</button><button className="clinical-action clinical-action--primary" disabled={saving || !canEdit} onClick={onConfirm} type="button">플래닝 확정</button></div>
  </div>;
}
