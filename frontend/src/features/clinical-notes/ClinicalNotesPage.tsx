import { useEffect, useMemo, useRef, useState } from "react";

import { getAIAnalyses } from "../ai-analysis/api";
import type { AIAnalysisItem } from "../ai-analysis/types";
import { getConsultations } from "../consultations/api";
import type { ConsultationListItem } from "../consultations/types";
import { getImagingStudies } from "../imaging/api";
import type { ImagingStudy } from "../imaging/types";
import { getPatientEncounters } from "../medication-safety/api";
import type { EncounterListItem } from "../medication-safety/types";
import { PatientHeader, PatientRail } from "../patients/PatientChart";
import { getPatients } from "../patients/api";
import type { Patient } from "../patients/types";
import { createClinicalNote, finalizeClinicalNote, getClinicalNote, getClinicalNotes, getInitialAssessmentsByEncounter, updateClinicalNote } from "./api";
import type { ClinicalNote, ClinicalNoteDraftFields, InitialAssessment, InitialAssessmentItem } from "./types";
import "./clinical-notes.css";

const EMPTY_DRAFT: ClinicalNoteDraftFields = { subjective: "", objective: "", assessment: "", plan: "", clinicalOpinion: "" };
const SOAP_FIELDS = [
  ["S", "Subjective (주관적 소견)", "subjective"],
  ["O", "Objective (객관적 소견)", "objective"],
  ["A", "Assessment (평가)", "assessment"],
  ["P", "Plan (계획)", "plan"],
  ["C", "통합 임상소견 (Clinical Opinion)", "clinicalOpinion"],
] as const;

function dateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ko-KR");
}
function encounterId(item: EncounterListItem) { return item.encounter_id ?? item.id ?? ""; }
function encounterRank(item: EncounterListItem) {
  if (item.status === "IN_PROGRESS") return 0;
  if (item.status === "REGISTERED") return 1;
  return 2;
}
function noteToDraft(note: ClinicalNote): ClinicalNoteDraftFields {
  return { subjective: note.subjective, objective: note.objective, assessment: note.assessment, plan: note.plan, clinicalOpinion: note.clinicalOpinion };
}
function operationError(error: unknown, fallback: string) {
  if (!(error instanceof Error)) return fallback;
  if (error.message.includes("CLINICAL_NOTE_ALREADY_IN_PROGRESS")) return "이 Encounter에 작성 중인 진료기록이 이미 있습니다.";
  if (error.message.includes("CLINICAL_NOTE_INCOMPLETE")) return "최종확정하려면 평가, 계획, 통합 임상소견을 모두 입력해야 합니다.";
  if (error.message.includes("CLINICAL_NOTE_INVALID_STATE")) return "DRAFT 상태의 진료기록만 수정하거나 확정할 수 있습니다.";
  return fallback;
}
function assessmentValue(item: InitialAssessmentItem | undefined) {
  if (!item) return null;
  const value = item.value_text ?? item.value_numeric ?? item.value;
  return value === undefined || value === null || value === ""
    ? null
    : `${String(value)}${item.unit ? ` ${item.unit}` : ""}`;
}

interface ClinicalNotesPageProps {
  /** Optional parent selection; the current workspace does not yet supply it. */
  selectedPatient?: Patient | null;
}

export default function ClinicalNotesPage({ selectedPatient: contextPatient = null }: ClinicalNotesPageProps) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [encounters, setEncounters] = useState<EncounterListItem[]>([]);
  const [notes, setNotes] = useState<ClinicalNote[]>([]);
  const [selectedNote, setSelectedNote] = useState<ClinicalNote | null>(null);
  const [draft, setDraft] = useState<ClinicalNoteDraftFields>(EMPTY_DRAFT);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [referenceLoading, setReferenceLoading] = useState(false);
  const [assessment, setAssessment] = useState<InitialAssessment | null>(null);
  const [studies, setStudies] = useState<ImagingStudy[]>([]);
  const [analyses, setAnalyses] = useState<AIAnalysisItem[]>([]);
  const [consultations, setConsultations] = useState<ConsultationListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);
  const automaticPatientId = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    getPatients().then((response) => { if (active) setPatients(response.results); })
      .catch(() => { if (active) setError("환자 목록을 불러오지 못했습니다."); })
      .finally(() => { if (active) setPatientsLoading(false); });
    return () => { active = false; };
  }, []);

  async function loadNote(note: ClinicalNote, expectedRequest = requestId.current) {
    setSelectedNote(note);
    setDraft(noteToDraft(note));
    try {
      const detail = await getClinicalNote(note.noteId);
      if (requestId.current === expectedRequest) { setSelectedNote(detail); setDraft(noteToDraft(detail)); }
    } catch {
      if (requestId.current === expectedRequest) setError("진료기록 상세를 불러오지 못했습니다.");
    }
  }

  async function loadNotes(patientEncounters: EncounterListItem[], expectedRequest: number) {
    const responses = await Promise.all(patientEncounters.map(encounterId).filter(Boolean).map((id) => getClinicalNotes(id)));
    if (requestId.current !== expectedRequest) return [];
    const nextNotes = responses.flatMap((response) => response.results).sort((left, right) =>
      (right.updatedAt ?? right.createdAt ?? "").localeCompare(left.updatedAt ?? left.createdAt ?? ""));
    setNotes(nextNotes);
    return nextNotes;
  }

  async function selectPatient(patient: Patient) {
    const currentRequest = ++requestId.current;
    setSelectedPatient(patient); setEncounters([]); setNotes([]); setSelectedNote(null); setDraft(EMPTY_DRAFT);
    setNotesLoading(true); setError(null);
    try {
      const patientEncounters = await getPatientEncounters(patient.id);
      if (requestId.current !== currentRequest) return;
      setEncounters(patientEncounters);
      const nextNotes = await loadNotes(patientEncounters, currentRequest);
      if (nextNotes[0]) await loadNote(nextNotes[0], currentRequest);
    } catch {
      if (requestId.current === currentRequest) setError("환자의 진료기록을 불러오지 못했습니다.");
    } finally {
      if (requestId.current === currentRequest) setNotesLoading(false);
    }
  }

  useEffect(() => {
    if (patientsLoading || selectedPatient || patients.length === 0) return;
    const preferredPatient = contextPatient
      ? patients.find((patient) => patient.id === contextPatient.id) ?? patients[0]
      : patients[0];
    if (automaticPatientId.current === preferredPatient.id) return;
    automaticPatientId.current = preferredPatient.id;
    void selectPatient(preferredPatient);
  }, [contextPatient, patients, patientsLoading, selectedPatient]);

  const sortedEncounters = useMemo(() => [...encounters].sort((left, right) =>
    encounterRank(left) - encounterRank(right) || (right.arrived_at ?? "").localeCompare(left.arrived_at ?? "")), [encounters]);
  const currentEncounter = sortedEncounters[0] ?? null;
  const activeEncounter = sortedEncounters.find((item) => item.status === "IN_PROGRESS" || item.status === "REGISTERED") ?? null;
  const readOnly = selectedNote?.status === "FINAL";
  const finalizeMissing = !draft.assessment.trim() || !draft.plan.trim() || !draft.clinicalOpinion.trim();
  const referenceEncounterId = selectedNote?.encounterId
    ?? (activeEncounter ? encounterId(activeEncounter) : currentEncounter ? encounterId(currentEncounter) : "");

  useEffect(() => {
    let active = true;
    setAssessment(null); setStudies([]); setAnalyses([]); setConsultations([]);
    if (!selectedPatient || !referenceEncounterId) { setReferenceLoading(false); return; }
    setReferenceLoading(true);
    void Promise.allSettled([
      getInitialAssessmentsByEncounter(referenceEncounterId),
      getImagingStudies({ patientId: selectedPatient.id }),
      getAIAnalyses(),
      getConsultations(),
    ]).then(([assessmentResult, studyResult, analysisResult, consultationResult]) => {
      if (!active) return;
      const nextStudies = studyResult.status === "fulfilled" ? studyResult.value : [];
      const studyIds = new Set(nextStudies.map((study) => study.id));
      setStudies(nextStudies);
      setAnalyses(analysisResult.status === "fulfilled"
        ? analysisResult.value.results.filter((item) => studyIds.has(item.study_id))
        : []);
      setConsultations(consultationResult.status === "fulfilled"
        ? consultationResult.value.results.filter((item) => item.encounter_id === referenceEncounterId)
        : []);
      setAssessment(assessmentResult.status === "fulfilled"
        ? assessmentResult.value.results[0] ?? null
        : null);
    }).finally(() => { if (active) setReferenceLoading(false); });
    return () => { active = false; };
  }, [referenceEncounterId, selectedPatient]);
  const assessmentItems = useMemo(
    () => new Map((assessment?.items ?? []).map((item) => [item.item_code, item])),
    [assessment],
  );
  const latestStudy = [...studies].sort((left, right) =>
    (right.study_at ?? "").localeCompare(left.study_at ?? ""))[0] ?? null;
  const latestAnalysis = [...analyses].sort((left, right) =>
    right.requested_at.localeCompare(left.requested_at))[0] ?? null;
  const latestConsultation = [...consultations].sort((left, right) =>
    right.requested_at.localeCompare(left.requested_at))[0] ?? null;

  async function startDraft() {
    const activeEncounterId = activeEncounter ? encounterId(activeEncounter) : "";
    if (!activeEncounterId) return;
    setSaving(true); setError(null);
    try {
      const note = await createClinicalNote({ encounterId: activeEncounterId });
      setNotes((current) => [note, ...current.filter((item) => item.noteId !== note.noteId)]);
      setSelectedNote(note); setDraft(noteToDraft(note));
    } catch (nextError) {
      setError(operationError(nextError, "새 SOAP 진료기록을 생성하지 못했습니다."));
    } finally { setSaving(false); }
  }

  async function saveDraft() {
    if (!selectedNote || readOnly) return;
    setSaving(true); setError(null);
    try {
      const updated = await updateClinicalNote(selectedNote.noteId, draft);
      setSelectedNote(updated); setDraft(noteToDraft(updated));
      setNotes((current) => current.map((note) => note.noteId === updated.noteId ? updated : note));
    } catch (nextError) {
      setError(operationError(nextError, "진료기록을 임시저장하지 못했습니다."));
    } finally { setSaving(false); }
  }

  async function finalizeDraft() {
    if (!selectedNote || readOnly || finalizeMissing) return;
    setSaving(true); setError(null);
    try {
      await updateClinicalNote(selectedNote.noteId, draft);
      const finalized = await finalizeClinicalNote(selectedNote.noteId);
      setSelectedNote(finalized); setDraft(noteToDraft(finalized));
      setNotes((current) => current.map((note) => note.noteId === finalized.noteId ? finalized : note));
    } catch (nextError) {
      setError(operationError(nextError, "진료기록을 최종확정하지 못했습니다."));
    } finally { setSaving(false); }
  }

  return <section className="patient-context-dashboard clinical-notes-dashboard"><div className="patient-workspace">
    <PatientRail selectedId={selectedPatient?.id ?? null} patients={patients} onSelect={(patient) => void selectPatient(patient)} />
    {selectedPatient && <PatientHeader patient={selectedPatient} care={{ arrivedAt: currentEncounter?.arrived_at, endedAt: currentEncounter?.ended_at, encounterStatus: currentEncounter?.status ?? "없음", encounterType: currentEncounter?.encounter_type }} />}
    {!selectedPatient ? <main className="patient-context-main patient-context-main--empty"><div className="patient-selection-empty">
      <strong>{patientsLoading || patients.length > 0 ? "환자 정보를 준비하는 중입니다." : "선택된 환자가 없습니다."}</strong>
      {!patientsLoading && patients.length === 0 && <span>조회된 환자 정보가 없습니다.</span>}
    </div></main> : <main className="patient-context-main clinical-notes-main">
      {error && <div className="clinical-notes-error" role="alert">{error}</div>}
      {!notesLoading && encounters.length === 0 && <div className="patient-encounter-state is-empty">조회 가능한 Encounter가 없습니다.</div>}
      <div className="clinical-notes-content"><section className="clinical-notes-reference-panel">
        <div className="clinical-notes-picker">
          <header><h2>진료기록</h2><button type="button" onClick={() => void startDraft()} disabled={!activeEncounter || saving} title={!activeEncounter ? "활성 Encounter가 있을 때만 작성할 수 있습니다." : undefined}>+ 새 기록 작성</button></header>
          <label><span>진료기록 선택</span><select value={selectedNote?.noteId ?? ""} disabled={notesLoading || notes.length === 0} onChange={(event) => {
            const note = notes.find((item) => item.noteId === event.target.value);
            if (note) void loadNote(note);
          }}><option value="">{notesLoading ? "불러오는 중" : "진료기록 없음"}</option>{notes.map((note) => <option key={note.noteId} value={note.noteId}>{dateTime(note.updatedAt ?? note.createdAt)} · {note.status}</option>)}</select></label>
        </div>
        <div className="clinical-notes-reference">
          <header><h2>진료 참고정보</h2></header>
          {referenceLoading ? <div className="clinical-notes-reference-empty">참고정보를 불러오는 중입니다.</div> : <>
            <article className="clinical-reference-assessment"><h3>초기평가 <small>간호사 작성</small></h3>
              {assessment ? <><dl>
                <div><dt>우선순위</dt><dd>{assessment.triage_priority ?? "-"}</dd></div>
                <div><dt>총점</dt><dd>{assessment.total_score ?? "-"}</dd></div>
                <div><dt>증상발생</dt><dd>{dateTime(assessment.onset_at)}</dd></div>
                <div><dt>마지막 정상(LKW)</dt><dd>{dateTime(assessment.lkw_at)}</dd></div>
                <div className="is-wide"><dt>주요 증상</dt><dd>{assessment.symptom_note || "-"}</dd></div>
              </dl><div className="clinical-reference-metrics"><section><strong>FAST</strong>{(["FAST_FACE", "FAST_ARM"] as const).map((code) => <span key={code}><i>{code.replace("FAST_", "")}</i><b>{assessmentValue(assessmentItems.get(code)) ?? "-"}</b></span>)}</section><section><strong>Vital</strong>{(["BP_SYS", "HEART_RATE"] as const).map((code) => <span key={code}><i>{code === "BP_SYS" ? "수축기 혈압" : "심박수"}</i><b>{assessmentValue(assessmentItems.get(code)) ?? "-"}</b></span>)}</section></div></> : <p>현재 Encounter에서 조회 가능한 assessment_id가 없습니다.</p>}
            </article>
            <div className="clinical-reference-links">
              <article><span>▣</span><div><strong>최근 영상검사</strong>{latestStudy ? <small>{latestStudy.modality} · {dateTime(latestStudy.study_at)} · {latestStudy.status}</small> : <small>조회된 영상검사가 없습니다.</small>}</div></article>
              <article><span>AI</span><div><strong>AI 분석 결과</strong>{latestAnalysis ? <small>{latestAnalysis.analysis_type} · {latestAnalysis.status}</small> : <small>조회된 AI 분석 결과가 없습니다.</small>}</div></article>
              <article><span>♧</span><div><strong>협진 상태</strong>{latestConsultation ? <small>{latestConsultation.type} · {latestConsultation.ui_status}</small> : <small>조회된 협진이 없습니다.</small>}</div></article>
            </div>
          </>}
        </div>
      </section><section className="clinical-notes-soap">
        <header><div><h2>SOAP</h2>{selectedNote && <span className={`is-${selectedNote.status.toLowerCase()}`}>{selectedNote.status}</span>}</div><small>{selectedNote ? `작성자 ID ${selectedNote.authorId || "-"}` : ""}</small></header>
        {!selectedNote ? <div className="clinical-notes-selection-empty"><strong>조회할 진료기록을 선택하거나 새 SOAP를 작성해 주세요.</strong></div> : <><div className="clinical-notes-soap-grid">
          {SOAP_FIELDS.map(([code, label, field]) => <label className={`clinical-notes-soap-field${field === "clinicalOpinion" ? " is-clinical-opinion" : ""}`} key={field}>
            <span><b>{code}</b><strong>{label}</strong></span><textarea value={draft[field]} readOnly={readOnly} disabled={saving} aria-label={label} onChange={(event) => setDraft((current) => ({ ...current, [field]: event.target.value }))} />
          </label>)}</div>
          <footer><span>수정 {dateTime(selectedNote.updatedAt)}{selectedNote.finalizedAt ? ` · 확정 ${dateTime(selectedNote.finalizedAt)}` : ""}</span>
            {readOnly ? <strong className="clinical-notes-readonly">최종확정 기록 · 읽기 전용</strong> : <><button type="button" onClick={() => void saveDraft()} disabled={saving}>{saving ? "저장 중" : "임시저장"}</button><button type="button" className="is-primary" onClick={() => void finalizeDraft()} disabled={saving || finalizeMissing} title={finalizeMissing ? "평가, 계획, 통합 임상소견을 모두 입력해 주세요." : undefined}>최종확정</button></>}
          </footer>
        </>}
      </section></div>
    </main>}
  </div></section>;
}
