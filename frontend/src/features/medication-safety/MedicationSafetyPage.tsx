import { useEffect, useMemo, useRef, useState } from "react";
import {
  checkPrescriptionSafety,
  createPrescription,
  finalizePrescription,
  searchMedications,
  updatePrescription,
} from "./api";
import type {
  DurAlert,
  MedicationItem,
  PrescriptionItemInput,
  PrescriptionItemResponse,
  PrescriptionResponse,
  SafetyCheckResponse,
} from "./types";
import { PatientHeader, PatientRail } from "../patients/PatientChart";
import { getPatients } from "../patients/api";
import type { Patient } from "../patients/types";
import "./medication-safety.css";

interface EditableItem extends PrescriptionItemInput {
  key: string;
  medication_code: string;
  medication_name: string;
  strength?: string;
}

const today = new Date().toISOString().slice(0, 10);

interface MedicationSafetyPageProps {
  context: {
    patient: Patient;
    encounterId: string | null;
  } | null;
  onSelectPatient?: (patient: Patient) => void;
  onOpenPatientChart?: (patient: Patient) => void;
}

function toEditable(item: PrescriptionItemResponse): EditableItem {
  return { ...item, key: item.item_id };
}

function requestError(error: unknown) {
  const message = error instanceof Error ? error.message : "";
  const status = message.match(/BACKEND_REQUEST_FAILED:(\d+)/)?.[1];
  if (status === "400") return "입력값을 확인해주세요.";
  if (status === "403") return "이 작업을 수행할 권한이 없거나 담당 진료 범위가 아닙니다.";
  if (status === "404") return "요청한 환자·진료·처방 정보를 찾지 못했습니다.";
  if (status === "409") return "처방 상태 또는 DUR 경고로 인해 요청을 완료하지 못했습니다.";
  if (status === "422") return "차단 경고를 재정의하려면 경고별 사유가 필요합니다.";
  if (status === "503") return "DUR 검증 서비스를 사용할 수 없습니다.";
  return "백엔드 요청에 실패했습니다.";
}

function severityLabel(severity: DurAlert["severity"]) {
  return { BLOCK: "금지", MAJOR: "경고", WARNING: "주의", INFO: "정보" }[severity];
}

function alertTypeLabel(type: DurAlert["alert_type"]) {
  return {
    DDI: "병용금기",
    DOSE: "용량주의",
    DUPLICATE: "효능군 중복",
    AGE: "특정연령 금기",
    ELDERLY: "노인주의",
    PREGNANCY: "임부금기",
    DURATION: "투여기간주의",
    ALLERGY: "알레르기",
  }[type];
}

function isUuid(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

export default function MedicationSafetyPage({ context, onSelectPatient, onOpenPatientChart }: MedicationSafetyPageProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MedicationItem[]>([]);
  const [resultCount, setResultCount] = useState(0);
  const [prescription, setPrescription] = useState<PrescriptionResponse | null>(null);
  const [items, setItems] = useState<EditableItem[]>([]);
  const [safety, setSafety] = useState<SafetyCheckResponse | null>(null);
  const [overrideReasons, setOverrideReasons] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [patientList, setPatientList] = useState<Patient[]>(context ? [context.patient] : []);
  const [patientListLoaded, setPatientListLoaded] = useState(false);
  const automaticPatientId = useRef<string | null>(null);
  const hasEncounter = Boolean(context?.encounterId);

  useEffect(() => {
    let active = true;
    void getPatients()
      .then((response) => {
        if (active) setPatientList(response.results);
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setPatientListLoaded(true);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!patientListLoaded || context || !patientList[0] || !onSelectPatient) return;
    if (automaticPatientId.current === patientList[0].id) return;
    automaticPatientId.current = patientList[0].id;
    onSelectPatient(patientList[0]);
  }, [context, onSelectPatient, patientList, patientListLoaded]);

  useEffect(() => {
    setQuery("");
    setResults([]);
    setResultCount(0);
    setPrescription(null);
    setItems([]);
    setSafety(null);
    setOverrideReasons({});
    setError(null);
    setNotice(null);
  }, [context?.patient.id]);

  const locked = prescription?.status === "FINAL";
  const blockingAlerts = useMemo(
    () => safety?.alerts.filter((alert) => alert.severity === "BLOCK" || alert.severity === "MAJOR") ?? [],
    [safety],
  );
  const alertCounts = useMemo(() => ({
    BLOCK: safety?.alerts.filter((alert) => alert.severity === "BLOCK").length ?? 0,
    MAJOR: safety?.alerts.filter((alert) => alert.severity === "MAJOR").length ?? 0,
    WARNING: safety?.alerts.filter((alert) => alert.severity === "WARNING").length ?? 0,
  }), [safety]);
  const safetyCriteria: Array<{ type: DurAlert["alert_type"]; label: string }> = [
    { type: "ALLERGY", label: "알레르기" },
    { type: "DDI", label: "약물 상호작용" },
    { type: "AGE", label: "연령 주의" },
    { type: "PREGNANCY", label: "임부·수유부" },
    { type: "DOSE", label: "용량 주의" },
    { type: "ELDERLY", label: "노인 주의" },
    { type: "DUPLICATE", label: "중복 처방" },
    { type: "DURATION", label: "투여기간 주의" },
  ];

  function relatedMedicationNames(alert: DurAlert) {
    return alert.related_medications
      .map((related) => {
        const medication = items.find((item) => item.medication_id === related);
        if (medication) return `${medication.medication_name}${medication.strength ? ` ${medication.strength}` : ""}`;
        return isUuid(related) ? null : related;
      })
      .filter((value): value is string => Boolean(value));
  }

  function begin(action: string) {
    setLoading(action);
    setError(null);
    setNotice(null);
  }

  function finish() {
    setLoading(null);
  }

  function invalidateSafety() {
    setSafety(null);
    setOverrideReasons({});
  }

  async function handleSearch() {
    if (!query.trim()) return;
    begin("search");
    try {
      const response = await searchMedications(query.trim());
      setResults(response.results);
      setResultCount(response.count);
    } catch (requestFailure) {
      setError(requestError(requestFailure));
    } finally {
      finish();
    }
  }

  function addMedication(medication: MedicationItem) {
    if (locked || items.some((item) => item.medication_id === medication.id)) return;
    setItems((current) => [
      ...current,
      {
        key: `new-${crypto.randomUUID()}`,
        medication_id: medication.id,
        medication_code: medication.medication_code,
        medication_name: medication.medication_name,
        strength: medication.strength,
        dose: 0,
        dose_unit: "mg",
        route: "PO",
        frequency_per_day: 1,
        timing: "식후",
        start_date: today,
        duration_days: 1,
        instructions: "",
      },
    ]);
    invalidateSafety();
  }

  function changeItem<K extends keyof EditableItem>(key: string, field: K, value: EditableItem[K]) {
    setItems((current) => current.map((item) => (item.key === key ? { ...item, [field]: value } : item)));
    invalidateSafety();
  }

  function prescriptionItems(): PrescriptionItemInput[] {
    return items.map((item) => ({
      ...(item.item_id ? { item_id: item.item_id } : {}),
      medication_id: item.medication_id,
      dose: item.dose,
      dose_unit: item.dose_unit,
      route: item.route,
      frequency_per_day: item.frequency_per_day,
      timing: item.timing,
      start_date: item.start_date,
      duration_days: item.duration_days,
      instructions: item.instructions,
    }));
  }

  function validateItems() {
    if (!items.length) return "처방 약물을 한 개 이상 추가해주세요.";
    if (items.some((item) => item.dose <= 0 || item.frequency_per_day < 1 || item.duration_days < 1)) {
      return "용량, 1일 횟수, 처방 기간은 1 이상이어야 합니다.";
    }
    if (items.some((item) => !item.dose_unit.trim() || !item.route.trim() || !item.timing.trim() || !item.start_date)) {
      return "처방 항목의 필수값을 모두 입력해주세요.";
    }
    return null;
  }

  async function saveDraft() {
    const validation = validateItems();
    if (validation) return setError(validation);
    if (!hasEncounter) return setError("처방 임시저장에는 진료 Encounter가 필요합니다.");
    begin("save");
    try {
      const response = prescription
        ? await updatePrescription(prescription.prescription_id, { items: prescriptionItems() })
        : await createPrescription({ encounter_id: context!.encounterId!, items: prescriptionItems() });
      setPrescription(response);
      setItems(response.items.map(toEditable));
      invalidateSafety();
      setNotice(`처방이 ${prescription ? "수정" : "임시저장"}되었습니다.`);
    } catch (requestFailure) {
      setError(requestError(requestFailure));
    } finally {
      finish();
    }
  }

  async function runSafetyCheck() {
    const validation = validateItems();
    if (validation) return setError(validation);
    if (!context) return setError("Worklist에서 진료 환자를 먼저 선택해주세요.");
    begin("safety");
    try {
      const response = await checkPrescriptionSafety({
        patient_id: context.patient.id,
        medications: items.map((item) => ({
          medication_id: item.medication_id,
          dose: item.dose,
          unit: item.dose_unit,
          frequency_per_day: item.frequency_per_day,
          duration_days: item.duration_days,
          route: item.route,
        })),
        ...(prescription?.status === "DRAFT" ? { draft_prescription_id: prescription.prescription_id } : {}),
      });
      setSafety(response);
      setNotice(response.safe ? "DUR 검증 결과 안전 경고가 없습니다." : `DUR 경고 ${response.alerts.length}건을 확인해주세요.`);
    } catch (requestFailure) {
      setError(requestError(requestFailure));
    } finally {
      finish();
    }
  }

  async function finalize() {
    if (!hasEncounter) return setError("처방 최종확정에는 진료 Encounter가 필요합니다.");
    if (!prescription || prescription.status !== "DRAFT") return setError("먼저 처방을 임시저장해주세요.");
    if (!safety) return setError("최종 확정 전에 DUR 검증을 실행해주세요.");
    const impossible = blockingAlerts.some((alert) => !alert.override_allowed);
    if (impossible) return setError("재정의가 허용되지 않은 차단 경고가 있어 확정할 수 없습니다.");
    if (blockingAlerts.some((alert) => !overrideReasons[alert.rule_id]?.trim())) {
      return setError("모든 금지·경고 항목에 재정의 사유를 입력해주세요.");
    }
    begin("finalize");
    try {
      const response = await finalizePrescription(
        prescription.prescription_id,
        blockingAlerts.map((alert) => ({
          alert_type: alert.alert_type,
          rule_type: alert.alert_type,
          rule_id: alert.rule_id,
          reason: overrideReasons[alert.rule_id].trim(),
        })),
      );
      setPrescription((current) => current ? { ...current, status: response.status, finalized_at: response.finalized_at } : current);
      setSafety({ ...safety, safe: response.safety.safe, alerts: response.safety.alerts });
      setNotice(`처방이 최종 확정되었습니다. 복약 일정 ${response.schedules_created}건이 생성되었습니다.`);
    } catch (requestFailure) {
      setError(requestError(requestFailure));
    } finally {
      finish();
    }
  }

  return (
    <section className="clinical-page medication-safety">
      <div className="medication-shell">
        <PatientRail selectedId={context?.patient.id ?? null} patients={patientList} onSelect={onSelectPatient} />
        <div className="medication-panel">
          {context ? <>
      <div className="medication-context medication-context--patient-header">
        <PatientHeader patient={context.patient} care={{ department: prescription?.department, clinician: prescription?.doctor }} onOpenDetails={() => onOpenPatientChart?.(context.patient)} />
      </div>

      {(error || notice) && <div className={`medication-feedback ${error ? "medication-feedback--error" : ""}`}>{error ?? notice}</div>}

      <div className="medication-workspace">
        <aside className="medication-clinical-column" aria-label="환자 임상정보">
          <article className="clinical-card medication-clinical-card">
            <div className="clinical-card__title medication-section-title"><h3><span aria-hidden="true">♧</span> 환자 임상정보</h3></div>
            <section className="medication-clinical-section">
              <div className="medication-clinical-section__heading"><strong>기본정보</strong></div>
              <dl className="medication-detail-list"><div><dt>환자번호</dt><dd>{context.patient.patient_no}</dd></div><div><dt>환자명</dt><dd>{context.patient.name}</dd></div><div><dt>성별 / 나이</dt><dd>{context.patient.sex ?? "-"} / {context.patient.estimated_age == null ? "-" : `${context.patient.estimated_age}세`}</dd></div><div><dt>진료과 / 담당의</dt><dd>{prescription?.department ?? "-"} / {prescription?.doctor ?? "-"}</dd></div></dl>
            </section>
            <section className="medication-clinical-section">
              <div className="medication-clinical-section__heading"><strong>주요 진단</strong></div>
              <div className="medication-compact-empty">진단 조회 API가 연결되지 않았습니다.</div>
            </section>
            <section className="medication-clinical-section">
              <div className="medication-clinical-section__heading"><strong>활력징후 (최근)</strong></div>
              <div className="medication-compact-empty">Vital 조회 API가 연결되지 않았습니다.</div>
            </section>
            <section className="medication-clinical-section medication-clinical-section--last">
              <div className="medication-clinical-section__heading"><strong>현재 복용 중인 약물</strong></div>
              <div className="medication-compact-empty">환자별 복용약 조회 API가 연결되지 않았습니다.</div>
            </section>
          </article>
        </aside>

        <main className="medication-column">
          <article className="clinical-card medication-search-card">
            <div className="clinical-card__title medication-section-title"><h3><span aria-hidden="true">⌕</span> 처방 작성</h3><small>약물 검색 결과 {resultCount}건</small></div>
            <div className="clinical-toolbar medication-search">
              <input aria-label="약물 검색" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="약물명, 성분명, 제조사로 검색하세요. (예: 아스피린, 클로피도그렐)" onKeyDown={(event) => { if (event.key === "Enter") void handleSearch(); }} />
              <button type="button" className="is-primary" disabled={loading !== null || !query.trim()} onClick={() => void handleSearch()}>검색</button>
              <button type="button" title="상세 검색 API 미제공" disabled>상세 검색⌄</button>
            </div>
            {loading === "search" ? <div className="clinical-state">검색 중...</div> : !results.length ? <div className="clinical-state">검색어를 입력하면 활성 약물 목록을 조회합니다.</div> : (
              <div className="clinical-table-wrap medication-search-results"><table className="clinical-table"><thead><tr><th>약물명</th><th>제형</th><th>함량</th><th>제조사</th><th>선택</th></tr></thead><tbody>{results.slice(0, 2).map((medication) => <tr key={medication.id}><td><strong>{medication.medication_name}</strong><small>{medication.medication_code}</small></td><td>{medication.dosage_form}</td><td>{medication.strength}</td><td>{medication.manufacturer}</td><td><button type="button" className="medication-add" disabled={locked || items.some((item) => item.medication_id === medication.id)} onClick={() => addMedication(medication)}>＋ 추가</button></td></tr>)}</tbody></table></div>
            )}
          </article>

          <article className="clinical-card medication-prescription-card">
            <div className="clinical-card__title medication-section-title"><h3><span aria-hidden="true">▣</span> 현재 처방 목록 ({items.length})</h3><button type="button" className="medication-clear" disabled={locked || !items.length || items.some((item) => Boolean(item.item_id))} title={items.some((item) => Boolean(item.item_id)) ? "저장된 항목 삭제 API가 제공되지 않습니다." : undefined} onClick={() => { setItems([]); invalidateSafety(); }}>전체 삭제</button></div>
            {!items.length ? <div className="clinical-state">검색 결과에서 처방 약물을 추가하거나 처방 ID로 기존 처방을 불러오세요.</div> : (
              <div className="medication-items">{items.map((item, index) => <div className="medication-item" key={item.key}>
                <div className="medication-item__heading"><span className="medication-item__number">{index + 1}</span><strong>{item.medication_name} {item.strength}</strong><span>{item.medication_code}</span><button type="button" disabled={locked || Boolean(item.item_id)} title={item.item_id ? "저장된 항목 삭제 API가 제공되지 않습니다." : undefined} onClick={() => { setItems((current) => current.filter((currentItem) => currentItem.key !== item.key)); invalidateSafety(); }}>삭제</button></div>
                <div className="medication-form-grid medication-form-grid--primary">
                  <label>1회 용량<input type="number" min="0.01" step="0.01" disabled={locked} value={item.dose || ""} onChange={(event) => changeItem(item.key, "dose", Number(event.target.value))} /></label>
                  <label>단위<input disabled={locked} value={item.dose_unit} onChange={(event) => changeItem(item.key, "dose_unit", event.target.value)} /></label>
                  <label>1일 횟수<input type="number" min="1" disabled={locked} value={item.frequency_per_day} onChange={(event) => changeItem(item.key, "frequency_per_day", Number(event.target.value))} /></label>
                  <label>기간(일)<input type="number" min="1" disabled={locked} value={item.duration_days} onChange={(event) => changeItem(item.key, "duration_days", Number(event.target.value))} /></label>
                </div>
                <details className="medication-item__details">
                  <summary>상세 설정</summary>
                  <div className="medication-form-grid medication-form-grid--details">
                    <label>투여 경로<input disabled={locked} value={item.route} onChange={(event) => changeItem(item.key, "route", event.target.value)} /></label>
                    <label>복용 시점<input disabled={locked} value={item.timing} onChange={(event) => changeItem(item.key, "timing", event.target.value)} /></label>
                    <label>시작일<input type="date" disabled={locked} value={item.start_date} onChange={(event) => changeItem(item.key, "start_date", event.target.value)} /></label>
                    <label className="medication-form-grid__wide">복약 지시<input disabled={locked} value={item.instructions} onChange={(event) => changeItem(item.key, "instructions", event.target.value)} /></label>
                  </div>
                </details>
              </div>)}</div>
            )}
            {!hasEncounter && <div className="medication-encounter-notice">진료 Encounter가 없어 처방 임시저장과 최종확정은 사용할 수 없습니다.</div>}
            <div className="clinical-action-bar medication-draft-actions"><button type="button" className="clinical-action" disabled={loading !== null || locked || !items.length || !hasEncounter} onClick={() => void saveDraft()}>{prescription ? "처방 수정·임시저장" : "처방 임시저장"}</button></div>
          </article>
        </main>

        <aside className="clinical-card medication-dur">
          <div className="clinical-card__title medication-section-title"><h3><span aria-hidden="true">♢</span> Medication Safety (DUR)</h3><button type="button" className="medication-recheck" disabled={loading !== null || locked || !items.length || !context} onClick={() => void runSafetyCheck()}>↻ 다시 검증</button></div>
          <div className="dur-summary">
            <div className="dur-summary--block"><span>금지</span><strong>{alertCounts.BLOCK}건</strong></div>
            <div className="dur-summary--major"><span>경고</span><strong>{alertCounts.MAJOR}건</strong></div>
            <div className="dur-summary--warning"><span>주의</span><strong>{alertCounts.WARNING}건</strong></div>
          </div>
          <div className="dur-criteria" aria-label="DUR 8종 안전성 검토 상태">
            {safetyCriteria.map((criterion) => {
              const alert = safety?.alerts.find((item) => item.alert_type === criterion.type);
              const status = !safety ? "검토 대기" : alert ? severityLabel(alert.severity) : "PASS";
              return <div key={criterion.type} className={`dur-criteria__item${alert ? ` dur-criteria__item--${alert.severity.toLowerCase()}` : ""}`}><span>{criterion.label} ({alertTypeLabel(criterion.type)})</span><strong>{status}</strong></div>;
            })}
          </div>
          {!safety ? <div className="clinical-state">환자 ID와 처방 항목을 입력한 뒤 실제 DUR 검증을 실행하세요.</div> : safety.alerts.length === 0 ? <div className="medication-safe">안전성 경고가 없습니다.</div> : <div className="dur-alerts">{safety.alerts.map((alert) => <div className={`dur-alert dur-alert--${alert.severity.toLowerCase()}`} key={`${alert.alert_type}-${alert.rule_id}`}>
            <div className="dur-alert__heading"><strong>{severityLabel(alert.severity)}</strong><b>{alertTypeLabel(alert.alert_type)}</b><span>중증도 {alert.severity === "BLOCK" ? "높음" : alert.severity === "MAJOR" ? "중간" : alert.severity === "WARNING" ? "낮음" : "정보"}</span></div>
            {!!relatedMedicationNames(alert).length && <p className="dur-alert__row"><b>관련 약물</b><span>{relatedMedicationNames(alert).join(" + ")}</span></p>}
            <p className="dur-alert__row"><b>설명</b><span>{alert.message || "상세 메시지가 제공되지 않았습니다."}</span></p>
            {alert.observed_daily_dose_mg != null && alert.max_daily_dose_mg != null && <div className="dur-comparison"><div><span>입력 일일용량</span><strong>{alert.observed_daily_dose_mg.toLocaleString()} <small>mg/day</small></strong></div><div><span>최대 허용용량</span><strong>{alert.max_daily_dose_mg.toLocaleString()} <small>mg/day</small></strong></div></div>}
            {alert.observed_duration_days != null && alert.max_duration_days != null && <div className="dur-comparison"><div><span>입력 투여기간</span><strong>{alert.observed_duration_days} <small>일</small></strong></div><div><span>최대 투여기간</span><strong>{alert.max_duration_days} <small>일</small></strong></div></div>}
            {(alert.severity === "BLOCK" || alert.severity === "MAJOR") && (alert.override_allowed ? <label className="dur-override"><span>Override 사유</span><textarea required maxLength={200} value={overrideReasons[alert.rule_id] ?? ""} onChange={(event) => setOverrideReasons((current) => ({ ...current, [alert.rule_id]: event.target.value }))} placeholder="사유를 입력하세요. (필수)" /></label> : <strong className="dur-alert__blocked">이 경고는 Override할 수 없습니다.</strong>)}
          </div>)}</div>}
          <div className="clinical-action-bar medication-dur__actions"><button type="button" className="clinical-action" disabled={loading !== null || locked || !items.length} onClick={() => void runSafetyCheck()}>↻ DUR 검증</button><button type="button" className="clinical-action medication-finalize" disabled={loading !== null || locked || !prescription || !hasEncounter} onClick={() => void finalize()}>✓ 처방 최종 확정</button></div>
        </aside>
      </div>
          </> : patientListLoaded && patientList.length === 0 ? <main className="medication-selection-empty clinical-card"><strong>선택된 환자가 없습니다.</strong><span>조회된 환자 데이터가 없습니다.</span></main> : <main className="medication-selection-empty clinical-card"><strong>환자 정보를 불러오는 중입니다.</strong></main>}
        </div>
      </div>
    </section>
  );
}
