import { useEffect } from "react";

import "./css/emergency_alert.css";

export type EmergencyAlertPriority = "EMERGENCY" | "URGENT";
export type EmergencyAlertTone = "positive" | "warning" | "danger" | "neutral";

export interface EmergencyAlertValue {
  value: string | number | null | undefined;
  tone?: EmergencyAlertTone;
}

export interface EmergencyPatientAlertProps {
  priority: EmergencyAlertPriority;
  eventId: string;
  patientId: string;
  patientNumber: string | null | undefined;
  patientName: string | null | undefined;
  sex: string | null | undefined;
  age: number | null | undefined;
  encounterId: string;
  visitAt: string | null | undefined;
  assessmentAt: string | null | undefined;
  symptomOnsetAt: string | null | undefined;
  lkwAt: string | null | undefined;
  assessorName: string | null | undefined;
  consciousness: string | number | null | undefined;
  fast: { face: EmergencyAlertValue; arm: EmergencyAlertValue; speech: EmergencyAlertValue };
  vitals: {
    systolicBp: EmergencyAlertValue;
    diastolicBp: EmergencyAlertValue;
    heartRate: EmergencyAlertValue;
    spo2: EmergencyAlertValue;
    bodyTemperature: EmergencyAlertValue;
  };
  allergy: string | null | undefined;
  mainSymptoms: string | null | undefined;
  specialNotes: string | null | undefined;
  currentIndex: number;
  totalCount: number;
  acknowledged: boolean;
  busy?: boolean;
  errorMessage?: string | null;
  onPrevious(): void;
  onNext(): void;
  onClose(): void;
  onAcknowledge(): void;
  onOpenPatient(): void;
}

const EMPTY_VALUE = "-";

function displayValue(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === "" ? EMPTY_VALUE : String(value);
}

function Metric({ icon, label, item, unit }: {
  icon: string;
  label: string;
  item: EmergencyAlertValue;
  unit?: string;
}) {
  const value = displayValue(item.value);
  const suffix = value === EMPTY_VALUE || !unit ? "" : ` ${unit}`;
  return (
    <div className="emergency-alert-metric">
      <span className="emergency-alert-metric-icon" aria-hidden="true">{icon}</span>
      <span className="emergency-alert-metric-label">{label}</span>
      <strong className={`emergency-alert-value is-${item.tone ?? "neutral"}`}>
        {value}{suffix}
      </strong>
    </div>
  );
}

function allergyIsPresent(value: string | null | undefined): boolean {
  const normalized = value?.trim().toLocaleLowerCase("ko-KR");
  return Boolean(
    normalized && normalized !== "없음" && normalized !== "none" && normalized !== "기록 없음",
  );
}

export default function EmergencyPatientAlert(props: EmergencyPatientAlertProps) {
  const {
    priority, patientNumber, patientName, sex, age, visitAt, assessmentAt,
    symptomOnsetAt, lkwAt, assessorName, consciousness, fast, vitals, allergy,
    mainSymptoms, specialNotes, currentIndex, totalCount, acknowledged,
    busy = false, errorMessage, onPrevious, onNext, onClose, onAcknowledge,
    onOpenPatient,
  } = props;
  const emergency = priority === "EMERGENCY";
  const title = emergency ? "응급 환자 발생" : "긴급 환자 발생";
  const actionMessage = emergency ? "즉시 진료가 필요합니다." : "빠른 진료가 필요합니다.";

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const bpMissing =
    displayValue(vitals.systolicBp.value) === EMPTY_VALUE &&
    displayValue(vitals.diastolicBp.value) === EMPTY_VALUE;

  return (
    <div className="emergency-alert-layer" role="presentation">
      <section
        className={`emergency-alert-modal ${emergency ? "is-emergency" : "is-urgent"}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="emergency-alert-title"
        aria-describedby="emergency-alert-description"
      >
        <header className="emergency-alert-header">
          <div className="emergency-alert-title">
            <span className="emergency-alert-siren" aria-hidden="true">!</span>
            <h2 id="emergency-alert-title">{title}</h2>
            <span className="emergency-alert-priority">{priority}</span>
          </div>
          <nav className="emergency-alert-pager" aria-label="연속 환자 알림">
            <button type="button" onClick={onPrevious} aria-label="이전 알림">‹</button>
            <strong aria-live="polite">{currentIndex} / {totalCount}</strong>
            <button type="button" onClick={onNext} aria-label="다음 알림">›</button>
          </nav>
          <button
            type="button"
            className="emergency-alert-icon-close"
            onClick={onClose}
            aria-label="팝업 닫기"
          >×</button>
        </header>

        <div className="emergency-alert-body">
          <section className="emergency-alert-patient-summary">
            <div className="emergency-alert-patient">
              <span className="emergency-alert-portrait" aria-hidden="true" />
              <div>
                <div className="emergency-alert-patient-name">
                  <h3>{displayValue(patientName)} <small>({displayValue(sex)} / {displayValue(age)})</small></h3>
                  <span className="emergency-alert-patient-priority">{priority}</span>
                </div>
                <dl>
                  <dt>환자번호</dt><dd>{displayValue(patientNumber)}</dd>
                  <dt>내원시각</dt><dd>{displayValue(visitAt)}</dd>
                </dl>
              </div>
            </div>
            <div className="emergency-alert-callout">
              <span aria-hidden="true">!</span>
              <div>
                <strong>{actionMessage}</strong>
                <p id="emergency-alert-description">
                  간호사 초기평가에서 {emergency ? "응급" : "긴급"} 소견이 확인되었습니다.
                  <br />환자 상태를 신속히 확인해 주세요.
                </p>
              </div>
            </div>
          </section>

          <div className="emergency-alert-clinical-grid">
            <section className="emergency-alert-card">
              <h4>초기평가 요약</h4>
              <dl className="emergency-alert-data-list">
                <div><dt>평가 시각</dt><dd>{displayValue(assessmentAt)}</dd></div>
                <div><dt>증상 발생 시간</dt><dd>{displayValue(symptomOnsetAt)}</dd></div>
                <div><dt>LKW</dt><dd>{displayValue(lkwAt)}</dd></div>
                <div><dt>평가자</dt><dd>{displayValue(assessorName)}</dd></div>
                <div><dt>의식 상태</dt><dd>{displayValue(consciousness)}</dd></div>
              </dl>
            </section>
            <section className="emergency-alert-card">
              <h4>FAST 평가 결과</h4>
              <div className="emergency-alert-metric-list">
                <Metric icon="F" label="안면 Face" item={fast.face} />
                <Metric icon="A" label="상지 Arm" item={fast.arm} />
                <Metric icon="S" label="언어 Speech" item={fast.speech} />
              </div>
            </section>
            <section className="emergency-alert-card">
              <h4>활력징후 <small>(Vital Sign)</small></h4>
              <div className="emergency-alert-metric-list emergency-alert-vitals">
                <Metric
                  icon="BP"
                  label="BP"
                  item={{
                    value: bpMissing ? null : `${displayValue(vitals.systolicBp.value)}/${displayValue(vitals.diastolicBp.value)}`,
                    tone: vitals.systolicBp.tone ?? vitals.diastolicBp.tone,
                  }}
                  unit="mmHg"
                />
                <Metric icon="HR" label="HR" item={vitals.heartRate} unit="bpm" />
                <Metric icon="O₂" label="SpO₂" item={vitals.spo2} unit="%" />
                <Metric icon="BT" label="BT" item={vitals.bodyTemperature} unit="℃" />
              </div>
            </section>
          </div>

          <section className="emergency-alert-card emergency-alert-additional">
            <h4>추가 정보</h4>
            <dl>
              <dt>주요 증상</dt><dd>{displayValue(mainSymptoms)}</dd>
              <dt>알레르기</dt>
              <dd className={allergyIsPresent(allergy) ? "has-allergy" : undefined}>{displayValue(allergy)}</dd>
              <dt>특이사항</dt><dd>{displayValue(specialNotes)}</dd>
            </dl>
          </section>
          {errorMessage && <p className="emergency-alert-error" role="alert">{errorMessage}</p>}
        </div>

        <footer className="emergency-alert-footer">
          <label className="emergency-alert-acknowledge">
            <input
              type="checkbox"
              checked={acknowledged}
              disabled={busy}
              onChange={(event) => { if (event.target.checked) onAcknowledge(); }}
            />
            <span>이 알림을 확인했습니다.</span>
          </label>
          <div className="emergency-alert-actions">
            <button type="button" className="is-secondary" onClick={onClose}>닫기</button>
            <button type="button" className="is-primary" disabled={busy} onClick={onOpenPatient}>
              환자 진료 화면으로 이동 <span aria-hidden="true">→</span>
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
