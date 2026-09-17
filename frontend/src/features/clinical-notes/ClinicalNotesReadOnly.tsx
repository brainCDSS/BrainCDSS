import { useEffect, useMemo, useRef, useState } from "react";

import {
  getClinicalNote,
  getClinicalNotes,
  getInitialAssessmentsByEncounter,
} from "./api";
import type {
  ClinicalNote,
  InitialAssessment,
  InitialAssessmentItem,
} from "./types";
import "./clinical-notes.css";

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

function assessmentValue(item: InitialAssessmentItem | undefined) {
  if (!item) return null;
  const value = item.value_text ?? item.value_numeric ?? item.value;
  return value === undefined || value === null || value === ""
    ? null
    : `${String(value)}${item.unit ? ` ${item.unit}` : ""}`;
}

interface ClinicalNotesReadOnlyProps {
  patientId: string;
  encounterId: string | null;
}

export default function ClinicalNotesReadOnly({
  patientId,
  encounterId,
}: ClinicalNotesReadOnlyProps) {
  const [notes, setNotes] = useState<ClinicalNote[]>([]);
  const [selectedNote, setSelectedNote] = useState<ClinicalNote | null>(null);
  const [assessment, setAssessment] = useState<InitialAssessment | null>(null);
  const [notesLoading, setNotesLoading] = useState(false);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [assessmentError, setAssessmentError] = useState<string | null>(null);
  const scopeRequestId = useRef(0);
  const noteRequestId = useRef(0);

  async function selectNote(
    note: ClinicalNote,
    expectedScopeRequest = scopeRequestId.current,
  ) {
    const requestId = ++noteRequestId.current;
    setSelectedNote(note);
    setNotesError(null);
    try {
      const detail = await getClinicalNote(note.noteId);
      if (
        scopeRequestId.current === expectedScopeRequest
        && noteRequestId.current === requestId
      ) {
        setSelectedNote(detail);
      }
    } catch {
      if (
        scopeRequestId.current === expectedScopeRequest
        && noteRequestId.current === requestId
      ) {
        setNotesError("진료기록 상세를 불러오지 못했습니다.");
      }
    }
  }

  useEffect(() => {
    const requestId = ++scopeRequestId.current;
    noteRequestId.current += 1;
    setNotes([]);
    setSelectedNote(null);
    setAssessment(null);
    setNotesError(null);
    setAssessmentError(null);

    if (!encounterId) {
      setNotesLoading(false);
      setAssessmentLoading(false);
      return;
    }

    setNotesLoading(true);
    setAssessmentLoading(true);

    void getClinicalNotes(encounterId).then((response) => {
      if (scopeRequestId.current !== requestId) return;
      setNotes(response.results);
      if (response.results[0]) {
        void selectNote(response.results[0], requestId);
      }
    }).catch(() => {
      if (scopeRequestId.current === requestId) {
        setNotesError("진료기록을 불러오지 못했습니다.");
      }
    }).finally(() => {
      if (scopeRequestId.current === requestId) setNotesLoading(false);
    });

    void getInitialAssessmentsByEncounter(encounterId).then((response) => {
      if (scopeRequestId.current === requestId) {
        setAssessment(response.results[0] ?? null);
      }
    }).catch(() => {
      if (scopeRequestId.current === requestId) {
        setAssessmentError("초기평가를 불러오지 못했습니다.");
      }
    }).finally(() => {
      if (scopeRequestId.current === requestId) setAssessmentLoading(false);
    });

    return () => {
      if (scopeRequestId.current === requestId) scopeRequestId.current += 1;
    };
  }, [encounterId, patientId]);

  const assessmentItems = useMemo(
    () => new Map((assessment?.items ?? []).map((item) => [item.item_code, item])),
    [assessment],
  );

  if (!encounterId) {
    return <section className="clinical-notes-main clinical-notes-readonly-main">
      <div className="clinical-notes-selection-empty">조회 가능한 진료정보가 없습니다.</div>
    </section>;
  }

  return <section className="clinical-notes-main clinical-notes-readonly-main">
    <div className="clinical-notes-content">
      <section className="clinical-notes-reference-panel">
        <div className="clinical-notes-picker">
          <header><h2>진료기록</h2></header>
          <label>
            <span>진료기록 선택</span>
            <select
              value={selectedNote?.noteId ?? ""}
              disabled={notesLoading || notes.length === 0}
              onChange={(event) => {
                const note = notes.find((item) => item.noteId === event.target.value);
                if (note) void selectNote(note);
              }}
            >
              <option value="">{notesLoading ? "불러오는 중" : "진료기록 없음"}</option>
              {notes.map((note) => <option key={note.noteId} value={note.noteId}>
                {dateTime(note.updatedAt ?? note.createdAt)} · {note.status}
              </option>)}
            </select>
          </label>
        </div>
        <div className="clinical-notes-reference">
          <header><h2>진료 참고정보</h2></header>
          {assessmentLoading ? <div className="clinical-notes-reference-empty">초기평가를 불러오는 중입니다.</div>
            : assessmentError ? <div className="clinical-notes-reference-empty">{assessmentError}</div>
              : <article className="clinical-reference-assessment">
                <h3>초기평가 <small>간호사 작성</small></h3>
                {assessment ? <>
                  <dl>
                    <div><dt>우선순위</dt><dd>{assessment.triage_priority ?? "-"}</dd></div>
                    <div><dt>총점</dt><dd>{assessment.total_score ?? "-"}</dd></div>
                    <div><dt>증상발생</dt><dd>{dateTime(assessment.onset_at)}</dd></div>
                    <div><dt>마지막 정상(LKW)</dt><dd>{dateTime(assessment.lkw_at)}</dd></div>
                    <div className="is-wide"><dt>주요 증상</dt><dd>{assessment.symptom_note || "-"}</dd></div>
                  </dl>
                  <div className="clinical-reference-metrics">
                    <section><strong>FAST</strong>{(["FAST_FACE", "FAST_ARM"] as const).map((code) => <span key={code}><i>{code.replace("FAST_", "")}</i><b>{assessmentValue(assessmentItems.get(code)) ?? "-"}</b></span>)}</section>
                    <section><strong>Vital</strong>{(["BP_SYS", "HEART_RATE"] as const).map((code) => <span key={code}><i>{code === "BP_SYS" ? "혈압" : "심박수"}</i><b>{assessmentValue(assessmentItems.get(code)) ?? "-"}</b></span>)}</section>
                  </div>
                </> : <p>현재 Encounter에 기록된 초기평가가 없습니다.</p>}
              </article>}
        </div>
      </section>
      <section className="clinical-notes-soap">
        <header>
          <div><h2>SOAP</h2>{selectedNote && <span className={`is-${selectedNote.status.toLowerCase()}`}>{selectedNote.status}</span>}</div>
          <small>{selectedNote ? `작성자 ID ${selectedNote.authorId || "-"}` : ""}</small>
        </header>
        {notesError ? <div className="clinical-notes-selection-empty">{notesError}</div>
          : !selectedNote ? <div className="clinical-notes-selection-empty">{notesLoading ? "진료기록을 불러오는 중입니다." : "진료기록이 없습니다."}</div>
            : <div className="clinical-notes-soap-grid">
              {SOAP_FIELDS.map(([code, label, field]) => <section className={`clinical-notes-soap-field${field === "clinicalOpinion" ? " is-clinical-opinion" : ""}`} key={field}>
                <span><b>{code}</b><strong>{label}</strong></span>
                <div className="clinical-notes-static-field">{selectedNote[field] || "-"}</div>
              </section>)}
            </div>}
      </section>
    </div>
  </section>;
}
