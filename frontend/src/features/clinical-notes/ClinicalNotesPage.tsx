import { useEffect, useMemo, useRef, useState } from "react";

import { getPatientEncounters } from "../medication-safety/api";
import type { EncounterListItem } from "../medication-safety/types";
import { PatientHeader, PatientRail } from "../patients/PatientChart";
import { getPatients } from "../patients/api";
import type { Patient } from "../patients/types";
import { getClinicalNote, getClinicalNotes } from "./api";
import type { ClinicalNote } from "./types";
import "./clinical-notes.css";

function dateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ko-KR");
}

function encounterId(item: EncounterListItem) {
  return item.encounter_id ?? item.id ?? "";
}

function encounterRank(item: EncounterListItem) {
  if (item.status === "IN_PROGRESS") return 0;
  if (item.status === "REGISTERED") return 1;
  return 2;
}

export default function ClinicalNotesPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [encounters, setEncounters] = useState<EncounterListItem[]>([]);
  const [notes, setNotes] = useState<ClinicalNote[]>([]);
  const [selectedNote, setSelectedNote] = useState<ClinicalNote | null>(null);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    let active = true;
    getPatients()
      .then((response) => { if (active) setPatients(response.results); })
      .catch(() => { if (active) setError("환자 목록을 불러오지 못했습니다."); })
      .finally(() => { if (active) setPatientsLoading(false); });
    return () => { active = false; };
  }, []);

  async function selectPatient(patient: Patient) {
    const currentRequest = ++requestId.current;
    setSelectedPatient(patient);
    setEncounters([]);
    setNotes([]);
    setSelectedNote(null);
    setNotesLoading(true);
    setError(null);
    try {
      const patientEncounters = await getPatientEncounters(patient.id);
      const noteResponses = await Promise.all(
        patientEncounters
          .map(encounterId)
          .filter(Boolean)
          .map((id) => getClinicalNotes(id)),
      );
      if (requestId.current !== currentRequest) return;
      const nextNotes = noteResponses
        .flatMap((response) => response.results)
        .sort((left, right) =>
          (right.updatedAt ?? right.createdAt ?? "").localeCompare(
            left.updatedAt ?? left.createdAt ?? "",
          ),
        );
      setEncounters(patientEncounters);
      setNotes(nextNotes);
      if (nextNotes[0]) await selectNote(nextNotes[0], currentRequest);
    } catch {
      if (requestId.current === currentRequest) {
        setError("환자의 진료기록을 불러오지 못했습니다.");
      }
    } finally {
      if (requestId.current === currentRequest) setNotesLoading(false);
    }
  }

  async function selectNote(note: ClinicalNote, expectedRequest = requestId.current) {
    setSelectedNote(note);
    try {
      const detail = await getClinicalNote(note.noteId);
      if (requestId.current === expectedRequest) setSelectedNote(detail);
    } catch {
      if (requestId.current === expectedRequest) {
        setError("진료기록 상세를 불러오지 못했습니다.");
      }
    }
  }

  const encounterById = useMemo(
    () => new Map(encounters.map((item) => [encounterId(item), item])),
    [encounters],
  );
  const currentEncounter = [...encounters].sort((left, right) =>
    encounterRank(left) - encounterRank(right) ||
    (right.arrived_at ?? "").localeCompare(left.arrived_at ?? ""),
  )[0] ?? null;

  return (
    <section className="patient-context-dashboard clinical-notes-dashboard">
      <div className="patient-workspace">
        <PatientRail
          selectedId={selectedPatient?.id ?? null}
          patients={patients}
          onSelect={(patient) => void selectPatient(patient)}
        />
        {selectedPatient && (
          <PatientHeader
            patient={selectedPatient}
            care={{
              arrivedAt: currentEncounter?.arrived_at,
              endedAt: currentEncounter?.ended_at,
              encounterStatus: currentEncounter?.status ?? "없음",
              encounterType: currentEncounter?.encounter_type,
            }}
          />
        )}
        {!selectedPatient ? (
          <main className="patient-context-main patient-context-main--empty">
            <div className="patient-selection-empty">
              <strong>{patientsLoading ? "환자 목록을 불러오는 중입니다." : "선택된 환자가 없습니다."}</strong>
              {!patientsLoading && <span>왼쪽 환자 목록에서 환자를 선택해 주세요.</span>}
            </div>
          </main>
        ) : (
          <main className="patient-context-main clinical-notes-main">
            {error && <div className="clinical-notes-error" role="alert">{error}</div>}
            {!notesLoading && encounters.length === 0 && (
              <div className="patient-encounter-state is-empty">조회 가능한 Encounter가 없습니다.</div>
            )}
            <div className="clinical-notes-content">
              <section className="clinical-notes-list-panel">
                <header><h2>진료기록 목록</h2><button type="button" disabled title="현재 Backend 쓰기 계약이 보장되지 않습니다.">+ SOAP 작성</button></header>
                {notesLoading ? <div className="clinical-notes-empty">진료기록을 불러오는 중입니다.</div> : notes.length ? notes.map((note) => {
                  const encounter = encounterById.get(note.encounterId);
                  return <button key={note.noteId} type="button" className={selectedNote?.noteId === note.noteId ? "is-selected" : ""} onClick={() => void selectNote(note)}>
                    <span><strong>{dateTime(note.updatedAt ?? note.createdAt)}</strong><em className={`is-${note.status.toLowerCase()}`}>{note.status}</em></span>
                    <small>Encounter {encounter?.encounter_no ?? note.encounterId}</small>
                    <small>{encounter?.encounter_type ?? "-"} · 작성자 ID {note.authorId || "-"}</small>
                  </button>;
                }) : <div className="clinical-notes-empty">등록된 진료기록이 없습니다.</div>}
              </section>

              <section className="clinical-notes-soap">
                <header><div><h2>SOAP</h2>{selectedNote && <span className={`is-${selectedNote.status.toLowerCase()}`}>{selectedNote.status}</span>}</div><small>{selectedNote ? `작성자 ID ${selectedNote.authorId || "-"}` : ""}</small></header>
                {!selectedNote ? <div className="clinical-notes-selection-empty"><strong>조회할 진료기록을 선택해 주세요.</strong></div> : <>
                  {([[
                    "S", "Subjective (주관적 소견)", selectedNote.subjective,
                  ], [
                    "O", "Objective (객관적 소견)", selectedNote.objective,
                  ], [
                    "A", "Assessment (평가)", selectedNote.assessment,
                  ], [
                    "P", "Plan (계획)", selectedNote.plan,
                  ]] as const).map(([code, label, value]) => <label className="clinical-notes-soap-field" key={code}>
                    <span><b>{code}</b><strong>{label}</strong></span>
                    <textarea value={value} readOnly aria-label={label} />
                  </label>)}
                  <footer>
                    <span>수정 {dateTime(selectedNote.updatedAt)}{selectedNote.finalizedAt ? ` · 확정 ${dateTime(selectedNote.finalizedAt)}` : ""}</span>
                    <button type="button" disabled title="현재 Backend PATCH/finalize 검증이 계약대로 동작하지 않습니다.">임시저장</button>
                    <button type="button" disabled title="현재 Backend PATCH/finalize 검증이 계약대로 동작하지 않습니다.">최종확정</button>
                  </footer>
                </>}
              </section>
            </div>
          </main>
        )}
      </div>
    </section>
  );
}
