import { useState } from "react";
import { MOCK_TREATMENT_OPTIONS } from "../mockData";
import type { PlacedClip, PlanningCase, VirtualClip } from "../types";

interface Props {
  planningCase: PlanningCase; clips: VirtualClip[]; placedClips: PlacedClip[]; selectedClip: PlacedClip | null;
  treatment: string; memo: string; saving: boolean; canEdit: boolean; error: string | null;
  onTreatmentChange: (value: string) => void; onMemoChange: (value: string) => void;
  onClipChange: (clip: PlacedClip) => void; onSelectClip: (id: string) => void;
  onDeleteClip: (id: string) => void; onDeleteAllClips: () => Promise<void>; onSave: () => void; onConfirm: () => void;
}
function NumberField({label,value,onChange,disabled}:{label:string;value:number;onChange:(value:number)=>void;disabled:boolean}) {
  return <label className="clip-number-field"><span>{label}</span><input type="number" value={value} disabled={disabled} onChange={event=>onChange(Number(event.target.value))}/></label>;
}
export default function PlanningControls({planningCase,clips,placedClips,selectedClip,treatment,memo,saving,canEdit,error,onTreatmentChange,onMemoChange,onClipChange,onSelectClip,onDeleteClip,onDeleteAllClips,onSave,onConfirm}:Props) {
  const [confirmDeleteAll,setConfirmDeleteAll]=useState(false);
  const position=(axis:"x"|"y"|"z",value:number)=>selectedClip&&onClipChange({...selectedClip,position:{...selectedClip.position,[axis]:value}});
  const rotation=(axis:"x"|"y"|"z",value:number)=>selectedClip&&onClipChange({...selectedClip,rotation:{...selectedClip.rotation,[axis]:value}});
  return <div className="planning-controls"><div className="planning-controls__body">
    <section className="planning-control-section planning-summary"><h4>AI 분석 요약</h4><dl className="planning-ai-summary"><div><dt>소견</dt><dd>{planningCase.aiSummary.finding}</dd></div><div><dt>신뢰도</dt><dd>{planningCase.aiSummary.confidence}</dd></div><div><dt>병변 위치</dt><dd>{planningCase.aiSummary.lesionLocation}</dd></div></dl></section>
    <section className="planning-control-section planning-treatment"><label className="clinical-field"><span>치료 방법</span><select value={treatment} disabled={!canEdit} onChange={event=>onTreatmentChange(event.target.value)}>{MOCK_TREATMENT_OPTIONS.map(option=><option key={option}>{option}</option>)}</select></label></section>
    <section className="planning-control-section planning-clip-settings"><h4>Clip 설정</h4><span className="planning-control-label">Clip 유형</span><div className="virtual-clip-library">{clips.map(clip=><button draggable={canEdit} key={clip.id} onDragStart={event=>{event.dataTransfer.effectAllowed="copy";event.dataTransfer.setData("application/x-braincdss-clip",clip.id)}} type="button"><span className={`virtual-clip-icon virtual-clip-icon--${clip.clipType.toLowerCase()}`}/><strong>{clip.name}</strong><small>{clip.clipType} · {clip.size} mm</small></button>)}</div>
      {selectedClip?<div className="clip-properties"><div className="clip-property-grid">{(["x","y","z"] as const).map(a=><NumberField key={a} label={a.toUpperCase()} value={selectedClip.position[a]} disabled={!canEdit} onChange={v=>position(a,v)}/>)}</div><div className="clip-property-grid">{(["x","y","z"] as const).map(a=><NumberField key={a} label={`R${a}`} value={selectedClip.rotation[a]} disabled={!canEdit} onChange={v=>rotation(a,v)}/>)}</div></div>:<p className="planning-compact-state">3D Viewer에 Clip을 배치하거나 선택하세요.</p>}
    </section>
    <section className="planning-control-section placed-clips-section"><div className="planning-section-heading"><h4>배치된 Clip ({placedClips.length})</h4>{placedClips.length>0&&<button className="planning-delete-button" disabled={!canEdit} onClick={()=>setConfirmDeleteAll(true)} type="button">모두 삭제</button>}</div>{confirmDeleteAll&&<div className="planning-delete-confirm" role="alertdialog" aria-label="배치된 Clip 모두 삭제 확인"><p>배치된 Clip을 모두 삭제하시겠습니까?</p><div><button type="button" onClick={()=>setConfirmDeleteAll(false)}>취소</button><button className="planning-delete-button" type="button" onClick={()=>{setConfirmDeleteAll(false);void onDeleteAllClips()}}>모두 삭제</button></div></div>}{placedClips.length?<div className="placed-clip-list">{placedClips.map((clip,index)=><div className={selectedClip?.instanceId===clip.instanceId?"is-selected":""} key={clip.instanceId}><button type="button" onClick={()=>onSelectClip(clip.instanceId)}>Clip {index+1} · {clip.clipType} {clip.size} mm</button><button className="planning-delete-button" disabled={!canEdit} onClick={()=>onDeleteClip(clip.instanceId)} type="button">삭제</button></div>)}</div>:<p className="planning-compact-state">배치된 Clip이 없습니다.</p>}</section>
    <section className="planning-control-section planning-memo"><label className="clinical-field"><span>플래닝 메모</span><textarea value={memo} disabled={!canEdit} maxLength={500} onChange={event=>onMemoChange(event.target.value)} placeholder="추가 메모를 입력하세요."/></label><small>{memo.length}/500</small></section>
    {error&&<p className="planning-compact-state" role="alert">{error}</p>}
  </div><div className="clinical-action-bar planning-actions"><button className="clinical-action" disabled={saving||!canEdit} onClick={onSave} type="button">{saving?"저장 중...":"임시 저장"}</button><button className="clinical-action clinical-action--primary" disabled={saving||!canEdit} onClick={onConfirm} type="button">플래닝 확정</button></div></div>;
}
