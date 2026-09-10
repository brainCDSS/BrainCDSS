import type { PlanningCase } from "../types";

import "./PatientPlanningContext.css";

function Row({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="planning-context__row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

type PatientPlanningContextProps = {
  planningCase: PlanningCase;
  hasPatient: boolean;
};

export default function PatientPlanningContext({
  planningCase,
  hasPatient,
}: PatientPlanningContextProps) {
  if (!hasPatient) {
    return (
      <aside
        className="clinical-card planning-context"
        aria-label="환자 및 검사 정보"
      >
        <div className="patient-context-empty">
          <div className="patient-context-empty__icon" aria-hidden="true">
            +
          </div>

          <strong>환자를 선택해주세요</strong>

          <p>
            상단에서 환자를 검색하거나 선택하면
            <br />
            환자 및 검사 정보가 표시됩니다.
          </p>
        </div>
      </aside>
    );
  }

  return (
    <aside
      className="clinical-card planning-context"
      aria-label="환자 및 검사 정보"
    >
      <div className="patient-context-header">
        <div className="patient-context-header__top">
          <span className="planning-eyebrow">
            PATIENT CONTEXT
          </span>

          <span
            className="planning-status-chip patient-context-header__status"
            title={planningCase.assignment.status}
          >
            {planningCase.assignment.status}
          </span>
        </div>

        <h3 className="patient-context-header__name">
          {planningCase.patient.name}
        </h3>
      </div>

      <dl className="planning-context__section">
        <Row
          label="환자번호"
          value={planningCase.patient.patientNo}
        />

        <Row
          label="성별 / 나이"
          value={`${planningCase.patient.sex} / ${planningCase.patient.age}`}
        />
      </dl>

      <div className="planning-context__divider" />

      <h4>검사 정보</h4>

      <dl className="planning-context__section">
        <Row
          label="진단"
          value={planningCase.examination.diagnosis}
        />

        <Row
          label="검사"
          value={planningCase.examination.studyName}
        />

        <Row
          label="검사일"
          value={planningCase.examination.studyDate}
        />
      </dl>

      <div className="planning-context__divider" />

      <h4>담당 정보</h4>

      <dl className="planning-context__section">
        <Row
          label="진료과"
          value={planningCase.assignment.department}
        />

        <Row
          label="담당의"
          value={planningCase.assignment.clinician}
        />
      </dl>
    </aside>
  );
}
