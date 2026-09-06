import { useState } from "react";

import type { Patient } from "./types";

import "./css/patient_chart.css";


/* =========================================================
   PatientChart Props
   ========================================================= */

interface PatientChartProps {
  /**
   * Header 검색에서 선택된 실제 환자 객체
   *
   * 환자 데이터를 직접 하드코딩하지 않는다.
   */
  patient: Patient;
}


/* =========================================================
   Patient Chart 내부 Tab 종류
   ========================================================= */

/**
 * Patient Chart 안에서 볼 수 있는 업무 영역
 *
 * 현재는 화면 구조만 만든다.
 *
 * 각 API가 연결되면
 * 해당 Tab 안에 실제 데이터를 넣을 예정이다.
 */
type PatientChartTab =
  | "clinical"
  | "lab"
  | "imaging"
  | "consultation"
  | "medication";


/* =========================================================
   Patient Chart 내부 Tab 설정
   ========================================================= */

/**
 * 화면에 보여줄 메뉴명과
 * 내부에서 사용할 id를 한 곳에서 관리한다.
 *
 * 실제 환자 데이터가 아니라
 * UI 메뉴 설정이므로 정적 선언 가능.
 */
const patientChartTabs: {
  id: PatientChartTab;
  label: string;
}[] = [
  {
    id: "clinical",
    label: "진료정보",
  },
  {
    id: "lab",
    label: "검사 / Lab",
  },
  {
    id: "imaging",
    label: "영상 · AI",
  },
  {
    id: "consultation",
    label: "협진",
  },
  {
    id: "medication",
    label: "처방 · DUR",
  },
];


/**
 * 환자 Chart
 *
 * 구성
 * ---------------------------------------------------------
 *
 * 1. Patient Chart 제목
 * 2. 환자 식별 + 기본정보
 * 3. 환자 내부 업무 Tab
 * 4. 선택한 Tab의 Content
 */
export default function PatientChart({
  patient,
}: PatientChartProps) {

  /* ========================================================
     1. 현재 선택된 Patient Chart 내부 Tab

     처음 환자 Chart를 열면
     진료정보가 기본 선택된다.
     ======================================================== */

  const [
    activeTab,
    setActiveTab,
  ] = useState<PatientChartTab>("clinical");


  /* ========================================================
     2. 선택한 Tab의 Content
     ======================================================== */

  /**
   * 현재 단계에서는 API를 임의로 만들지 않고
   * 어떤 영역이 선택되었는지만 표시한다.
   *
   * 다음 단계부터
   * 진료정보 → 실제 API
   * 검사/Lab → 실제 API
   *
   * 순서대로 연결한다.
   */
  function renderTabContent() {
    switch (activeTab) {

      /* -----------------------------------------------------
         진료정보
         ----------------------------------------------------- */

      case "clinical":
        return (
          <div className="patient-chart-empty">
            진료정보 API 연동 예정
          </div>
        );


      /* -----------------------------------------------------
         검사 / Lab
         ----------------------------------------------------- */

      case "lab":
        return (
          <div className="patient-chart-empty">
            검사 / Lab API 연동 예정
          </div>
        );


      /* -----------------------------------------------------
         영상 / AI
         ----------------------------------------------------- */

      case "imaging":
        return (
          <div className="patient-chart-empty">
            영상 / AI API 연동 예정
          </div>
        );


      /* -----------------------------------------------------
         협진
         ----------------------------------------------------- */

      case "consultation":
        return (
          <div className="patient-chart-empty">
            협진 API 연동 예정
          </div>
        );


      /* -----------------------------------------------------
         처방 / DUR
         ----------------------------------------------------- */

      case "medication":
        return (
          <div className="patient-chart-empty">
            처방 / DUR API 연동 예정
          </div>
        );
    }
  }


  return (
    <section className="patient-chart">

      {/* =====================================================
          1. Patient Chart 화면 제목
          ===================================================== */}

      <div className="patient-chart-page-heading">

        <span className="patient-chart-label">
          PATIENT CHART
        </span>

        <p>
          환자 기본정보 및 진료 정보를 확인합니다.
        </p>

      </div>


      {/* =====================================================
          2. 환자 식별 + 기본정보

          여기 디자인은 완료했으므로
          이번 단계에서는 건드리지 않는다.
          ===================================================== */}

      <section className="patient-identity-card">

        {/* 환자명 + 환자번호 */}
        <div className="patient-identity-header">

          <h2>
            {patient.name}
          </h2>

          <span className="patient-identity-number">
            {patient.patient_no}
          </span>

        </div>


        {/* 환자 기본정보 */}
        <div className="patient-identity-info">

          {/* 성별 */}
          <div className="patient-identity-item">
            <span>
              성별
            </span>

            <strong>
              {patient.sex ?? "-"}
            </strong>
          </div>


          {/* 생년월일 */}
          <div className="patient-identity-item">
            <span>
              생년월일
            </span>

            <strong>
              {patient.birth_date ?? "-"}
            </strong>
          </div>


          {/* 나이 */}
          <div className="patient-identity-item">
            <span>
              나이
            </span>

            <strong>
              {patient.estimated_age !== null
                ? `${patient.estimated_age}세`
                : "-"}
            </strong>
          </div>


          {/* 연락처 */}
          <div className="patient-identity-item">
            <span>
              연락처
            </span>

            <strong>
              {patient.phone ?? "-"}
            </strong>
          </div>


          {/* 상태 */}
          <div className="patient-identity-item">
            <span>
              상태
            </span>

            <strong>
              {patient.status}
            </strong>
          </div>

        </div>

      </section>


      {/* =====================================================
          3. Patient Chart 내부 업무 영역
          ===================================================== */}

      <section className="patient-chart-section">

        {/* ===================================================
            내부 Tab 메뉴

            예:
            진료정보 | 검사/Lab | 영상·AI | 협진 | 처방·DUR
            =================================================== */}

        <div
          className="patient-chart-tabs"
          role="tablist"
          aria-label="환자 진료정보 메뉴"
        >

          {patientChartTabs.map((tab) => {

            /**
             * 현재 선택된 Tab인지 확인
             */
            const isActive =
              activeTab === tab.id;


            return (
              <button
                key={tab.id}
                type="button"

                role="tab"

                aria-selected={isActive}

                className={
                  isActive
                    ? "patient-chart-tab active"
                    : "patient-chart-tab"
                }

                /**
                 * 클릭한 메뉴를
                 * 현재 activeTab으로 변경한다.
                 */
                onClick={() => {
                  setActiveTab(tab.id);
                }}
              >
                {tab.label}
              </button>
            );
          })}

        </div>


        {/* ===================================================
            4. 선택한 Tab의 실제 Content
            =================================================== */}

        <div className="patient-chart-tab-content">
          {renderTabContent()}
        </div>

      </section>

    </section>
  );
}