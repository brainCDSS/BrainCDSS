import { useState } from "react";

import type { Patient } from "./types";

import "./css/patient_chart.css";


interface PatientChartProps {
  patient: Patient;
  patients?: Patient[];
  onSelectPatient?: (patient: Patient) => void;
  onBackToList?: () => void;
}

type PatientChartTab =
  | "basic"
  | "clinical"
  | "imaging"
  | "medication"
  | "consultation";

const patientChartTabs: Array<{ id: PatientChartTab; label: string }> = [
  { id: "basic", label: "기본정보" },
  { id: "clinical", label: "임상데이터" },
  { id: "imaging", label: "영상 · AI" },
  { id: "medication", label: "처방 · DUR" },
  { id: "consultation", label: "협진 · 진료" },
];


export default function PatientChart({
  patient,
  patients = [],
  onSelectPatient,
  onBackToList,
}: PatientChartProps) {
  const [activeTab, setActiveTab] = useState<PatientChartTab>("basic");
  const [isRailPinned, setIsRailPinned] = useState(false);
  const hasPatientRail = patients.length > 0 && Boolean(onSelectPatient);


  function renderTabContent() {
    if (activeTab === "basic") {
      return (
        <div className="patient-chart-basic">
          <section className="patient-chart-info-section">
            <h3>기본 정보</h3>
            <dl className="patient-chart-info-grid">
              <div><dt>환자번호</dt><dd>{patient.patient_no}</dd></div>
              <div><dt>이름</dt><dd>{patient.name}</dd></div>
              <div><dt>생년월일</dt><dd>{patient.birth_date ?? "-"}</dd></div>
              <div><dt>나이</dt><dd>{patient.estimated_age !== null ? `${patient.estimated_age}세` : "-"}</dd></div>
              <div><dt>성별</dt><dd>{patient.sex ?? "-"}</dd></div>
              <div><dt>연락처</dt><dd>{patient.phone ?? "-"}</dd></div>
              <div><dt>상태</dt><dd><span className={`patient-status is-${patient.status.toLowerCase()}`}>{patient.status}</span></dd></div>
            </dl>
          </section>

          <section className="patient-chart-management">
            <h3>관리 정보</h3>
            <span>환자 ID</span>
            <code>{patient.id}</code>
          </section>
        </div>
      );
    }

    const emptyMessages: Record<Exclude<PatientChartTab, "basic">, { title: string; description: string }> = {
      clinical: {
        title: "임상데이터",
        description: "연결된 임상 데이터가 없습니다. API 연동 후 이 영역에 표시됩니다.",
      },
      imaging: {
        title: "영상 · AI",
        description: "연결된 영상 및 AI 분석 결과가 없습니다.",
      },
      medication: {
        title: "처방 · DUR",
        description: "연결된 처방 및 DUR 정보가 없습니다.",
      },
      consultation: {
        title: "협진 · 진료",
        description: "연결된 협진 및 진료 정보가 없습니다.",
      },
    };
    const message = emptyMessages[activeTab];

    return (
      <div className="patient-chart-empty">
        <strong>{message.title}</strong>
        <p>{message.description}</p>
      </div>
    );
  }


  return (
    <section className={isRailPinned ? "patient-detail-layout is-pinned" : "patient-detail-layout"}>
      {hasPatientRail && (
        <div className="patient-rail-wrap">
          <aside className="patient-rail" aria-label="열린 환자 목록">
            <header className="patient-rail-header">
              <div>
                <strong>환자 목록</strong>
                <small>마우스를 올리면 펼쳐집니다.</small>
              </div>
              <button
                type="button"
                className={isRailPinned ? "patient-rail-pin is-active" : "patient-rail-pin"}
                onClick={() => setIsRailPinned((previous) => !previous)}
                aria-pressed={isRailPinned}
                title={isRailPinned ? "환자 목록 고정 해제" : "환자 목록 고정"}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                  <path d="m14 4 6 6-3 1-4 4-1 5-3-3-5 3 3-5 4-4 1-3Z" />
                </svg>
              </button>
            </header>

            <div className="patient-rail-list">
              {patients.map((railPatient) => (
                <button
                  key={railPatient.id}
                  type="button"
                  className={railPatient.id === patient.id ? "patient-rail-item is-selected" : "patient-rail-item"}
                  onClick={() => onSelectPatient?.(railPatient)}
                  title={`${railPatient.name} · ${railPatient.patient_no}`}
                >
                  <strong>{railPatient.name}</strong>
                  <span className="patient-rail-details">
                    <small>{railPatient.patient_no}</small>
                    <small>{railPatient.sex ?? "-"} · {railPatient.estimated_age !== null ? `${railPatient.estimated_age}세` : "-"}</small>
                    <small>{railPatient.status}</small>
                  </span>
                </button>
              ))}
            </div>
          </aside>
        </div>
      )}

      <article className="patient-chart">
        <header className="patient-chart-toolbar">
          <div>
            <strong>Patient Chart</strong>
            <span>선택 환자 상세정보</span>
          </div>
          {onBackToList && (
            <button type="button" onClick={onBackToList}>환자 목록 전체 보기</button>
          )}
        </header>

        <section className="patient-identity-card">
          <div className="patient-identity-header">
            <div>
              <h2>{patient.name}</h2>
              <span className="patient-identity-number">{patient.patient_no}</span>
            </div>
            <span className={`patient-status is-${patient.status.toLowerCase()}`}>{patient.status}</span>
          </div>

          <div className="patient-identity-info">
            <div><span>생년월일</span><strong>{patient.birth_date ?? "-"}</strong></div>
            <div><span>나이</span><strong>{patient.estimated_age !== null ? `${patient.estimated_age}세` : "-"}</strong></div>
            <div><span>성별</span><strong>{patient.sex ?? "-"}</strong></div>
            <div><span>연락처</span><strong>{patient.phone ?? "-"}</strong></div>
          </div>
        </section>

        <section className="patient-chart-section">
          <div className="patient-chart-tabs" role="tablist" aria-label="환자 진료정보 메뉴">
            {patientChartTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                className={activeTab === tab.id ? "patient-chart-tab active" : "patient-chart-tab"}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="patient-chart-tab-content">{renderTabContent()}</div>
        </section>
      </article>
    </section>
  );
}
