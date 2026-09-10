import type { PlanningCase } from "../types";

function Row({ label, value }: { label: string; value: string }) {
  return <div className="planning-context__row"><dt>{label}</dt><dd>{value}</dd></div>;
}

export default function PatientPlanningContext({ planningCase }: { planningCase: PlanningCase }) {
  return <aside className="clinical-card planning-context" aria-label="환자 및 검사 정보">
    <div className="clinical-card__title planning-context__title"><div><span className="planning-eyebrow">PATIENT CONTEXT</span><h3>{planningCase.patient.name}</h3></div><span className="planning-status-chip">{planningCase.assignment.status}</span></div>
    <dl className="planning-context__section"><Row label="환자번호" value={planningCase.patient.patientNo}/><Row label="성별 / 나이" value={`${planningCase.patient.sex} / ${planningCase.patient.age}`}/></dl>
    <div className="planning-context__divider"/><h4>검사 정보</h4>
    <dl className="planning-context__section"><Row label="진단" value={planningCase.examination.diagnosis}/><Row label="검사" value={planningCase.examination.studyName}/><Row label="검사일" value={planningCase.examination.studyDate}/></dl>
    <div className="planning-context__divider"/><h4>담당 정보</h4>
    <dl className="planning-context__section"><Row label="진료과" value={planningCase.assignment.department}/><Row label="담당의" value={planningCase.assignment.clinician}/></dl>
  </aside>;
}
