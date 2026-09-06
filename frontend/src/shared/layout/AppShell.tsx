import { useState } from "react";
import type { ReactNode } from "react";

import AssessmentWorklist from "../../features/assessments/AssessmentWorklist";
import PatientChart from "../../features/patients/PatientChart";
import TriageAssessment from "../../features/assessments/TriageAssessment";
import ConsultationList from "../../features/consultations/ConsultationList";
import ConsultationPatientReview from "../../features/consultations/ConsultationPatientReview";

import type { Patient } from "../../features/patients/types";
import type { SidebarMenuKey } from "./Sidebar";

import Header from "./Header";
import Sidebar from "./Sidebar";
import WorkspaceTabs from "./WorkspaceTabs";

import "./layout.css";


interface AppShellProps {
  /**
   * 기본 화면
   *
   * 현재 App.tsx에서 Dashboard가
   * children으로 들어온다.
   */
  children: ReactNode;
}


/* =========================================================
   현재 진행 중인 Triage Context
   ---------------------------------------------------------
   Worklist에서 Triage를 열 때 확보한

   - assessment_id
   - encounter_id

   를 AppShell에서 보관한다.
   ========================================================= */

interface ActiveAssessmentContext {
  assessmentId: string;
  encounterId: string;
}


/**
 * Brain CDSS 공통 Layout
 *
 * 현재 Content 전환
 * ---------------------------------------------------------
 *
 * Dashboard
 * → children
 *
 * Worklist
 * → AssessmentWorklist
 *
 * 접수 / Triage
 * → TriageAssessment
 *
 * 협진
 * → ConsultationList
 * → ConsultationPatientReview
 *
 * 환자 검색 후 선택
 * → PatientChart
 */
export default function AppShell({
  children,
}: AppShellProps) {


  /* ========================================================
     1. Sidebar 접힘 상태
     ======================================================== */

  const [
    sidebarCollapsed,
    setSidebarCollapsed,
  ] = useState(false);


  /* ========================================================
     2. 현재 선택된 Sidebar 메뉴
     ======================================================== */

  const [
    activeMenu,
    setActiveMenu,
  ] = useState<SidebarMenuKey>(
    "dashboard",
  );


  /* ========================================================
     3. 현재 열려 있는 환자 Chart Tabs
     ======================================================== */

  const [
    openPatientTabs,
    setOpenPatientTabs,
  ] = useState<Patient[]>([]);


  /* ========================================================
     4. 현재 활성화된 환자
     ======================================================== */

  const [
    activePatientId,
    setActivePatientId,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     5. 현재 진행 중인 Assessment
     ======================================================== */

  const [
    activeAssessmentContext,
    setActiveAssessmentContext,
  ] = useState<ActiveAssessmentContext | null>(
    null,
  );


  /* ========================================================
     6. 현재 검토 중인 협진
     --------------------------------------------------------
     null
     → 협진 목록

     consultation_id
     → 해당 Patient Review
     ======================================================== */

  const [
    activeConsultationId,
    setActiveConsultationId,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     7. 현재 활성 환자 객체
     ======================================================== */

  const activePatient =
    activePatientId === null
      ? null
      : openPatientTabs.find(
          (patient) =>
            patient.id === activePatientId,
        ) ?? null;


  /* ========================================================
     8. Sidebar 접기 / 펼치기
     ======================================================== */

  const handleToggleSidebar = () => {

    setSidebarCollapsed(
      (previous) => !previous,
    );

  };


  /* ========================================================
     9. Sidebar 메뉴 선택
     ======================================================== */

  const handleMenuSelect = (
    menu: SidebarMenuKey,
  ) => {

    /**
     * 현재 실제 화면까지 구현된 메뉴만
     * Content 전환을 허용한다.
     */
    if (
      menu !== "dashboard" &&
      menu !== "worklist" &&
      menu !== "triage" &&
      menu !== "consultations"
    ) {
      return;
    }


    /**
     * Sidebar 메뉴로 이동할 경우
     * Patient Chart 활성 상태 해제
     */
    setActivePatientId(
      null,
    );


    /**
     * 기존 Assessment Context 해제
     */
    setActiveAssessmentContext(
      null,
    );


    /**
     * 기존 협진 상세 화면 해제
     *
     * Sidebar에서 협진 메뉴를 다시 누르면
     * Patient Review가 아니라 목록부터 시작한다.
     */
    setActiveConsultationId(
      null,
    );


    /**
     * 선택한 메뉴 저장
     */
    setActiveMenu(
      menu,
    );

  };


  /* ========================================================
     10. Worklist → Triage 열기
     ======================================================== */

  const handleOpenTriage = (
    assessmentId: string,
    encounterId: string,
  ) => {

    setActiveAssessmentContext({
      assessmentId,
      encounterId,
    });


    setActivePatientId(
      null,
    );


    setActiveConsultationId(
      null,
    );


    setActiveMenu(
      "triage",
    );

  };


  /* ========================================================
     11. 협진 목록 → Patient Review
     ======================================================== */

  const handleOpenConsultationReview = (
    consultationId: string,
  ) => {

    /**
     * 다른 업무 Context 해제
     */
    setActivePatientId(
      null,
    );


    setActiveAssessmentContext(
      null,
    );


    /**
     * 선택한 협진 ID 저장
     */
    setActiveConsultationId(
      consultationId,
    );


    /**
     * Sidebar 선택 상태는 협진 유지
     */
    setActiveMenu(
      "consultations",
    );

  };


  /* ========================================================
     12. Patient Review → 협진 목록
     ======================================================== */

  const handleBackToConsultationList = () => {

    setActiveConsultationId(
      null,
    );


    setActiveMenu(
      "consultations",
    );

  };


  /* ========================================================
     13. Header에서 환자 선택
     ======================================================== */

  const handlePatientSelect = (
    patient: Patient,
  ) => {

    setOpenPatientTabs(
      (previousTabs) => {

        const alreadyOpen =
          previousTabs.some(
            (openedPatient) =>
              openedPatient.id === patient.id,
          );


        if (alreadyOpen) {
          return previousTabs;
        }


        return [
          ...previousTabs,
          patient,
        ];

      },
    );


    /**
     * 다른 업무 Context 해제
     */
    setActiveAssessmentContext(
      null,
    );


    setActiveConsultationId(
      null,
    );


    /**
     * 검색한 환자 Chart 활성화
     */
    setActivePatientId(
      patient.id,
    );

  };


  /* ========================================================
     14. Dashboard Workspace Tab 선택
     ======================================================== */

  const handleSelectDashboard = () => {

    setActivePatientId(
      null,
    );


    setActiveAssessmentContext(
      null,
    );


    setActiveConsultationId(
      null,
    );


    setActiveMenu(
      "dashboard",
    );

  };


  /* ========================================================
     15. 환자 Chart Tab 선택
     ======================================================== */

  const handleSelectPatientTab = (
    patientId: string,
  ) => {

    setActiveAssessmentContext(
      null,
    );


    setActiveConsultationId(
      null,
    );


    setActivePatientId(
      patientId,
    );

  };


  /* ========================================================
     16. 환자 Chart Tab 닫기
     ======================================================== */

  const handleClosePatientTab = (
    patientId: string,
  ) => {

    setOpenPatientTabs(
      (previousTabs) =>
        previousTabs.filter(
          (patient) =>
            patient.id !== patientId,
        ),
    );


    if (
      activePatientId === patientId
    ) {

      setActivePatientId(
        null,
      );


      setActiveMenu(
        "dashboard",
      );

    }

  };


  /* ========================================================
     17. Main Content 결정
     ======================================================== */

  function renderMainContent() {


    /* -------------------------------------------------------
       환자 Chart
       ------------------------------------------------------- */

    if (activePatient) {

      return (
        <PatientChart
          patient={
            activePatient
          }
        />
      );

    }


    /* -------------------------------------------------------
       Worklist
       ------------------------------------------------------- */

    if (activeMenu === "worklist") {

      return (
        <AssessmentWorklist
          onOpenTriage={
            handleOpenTriage
          }
        />
      );

    }


    /* -------------------------------------------------------
       접수 / Triage
       ------------------------------------------------------- */

    if (activeMenu === "triage") {

      const triageKey =
        activeAssessmentContext
          ? `${activeAssessmentContext.assessmentId}:${activeAssessmentContext.encounterId}`
          : "triage-direct";


      return (
        <TriageAssessment
          key={
            triageKey
          }

          assessmentId={
            activeAssessmentContext?.assessmentId ??
            null
          }

          encounterId={
            activeAssessmentContext?.encounterId ??
            null
          }
        />
      );

    }


    /* -------------------------------------------------------
       협진
       -------------------------------------------------------

       activeConsultationId 없음
       → CON-002 협진 목록

       activeConsultationId 있음
       → CON-003 Patient Review
       ------------------------------------------------------- */

    if (activeMenu === "consultations") {


      /**
       * 협진 상세 Review
       */
      if (activeConsultationId) {

        return (
          <ConsultationPatientReview
            consultationId={
              activeConsultationId
            }
            onBack={
              handleBackToConsultationList
            }
          />
        );

      }


      /**
       * 협진 목록
       */
      return (
        <ConsultationList
          onOpenReview={
            handleOpenConsultationReview
          }
        />
      );

    }


    /* -------------------------------------------------------
       기본 Dashboard
       ------------------------------------------------------- */

    return children;

  }


  /* ========================================================
     18. Layout
     ======================================================== */

  return (

    <div
      className={
        sidebarCollapsed
          ? "app-shell sidebar-collapsed"
          : "app-shell"
      }
    >


      {/* =====================================================
          Header
          ===================================================== */}

      <Header
        onPatientSelect={
          handlePatientSelect
        }
      />


      {/* =====================================================
          Workspace Tabs
          ===================================================== */}

      <WorkspaceTabs
        sidebarCollapsed={
          sidebarCollapsed
        }

        onToggleSidebar={
          handleToggleSidebar
        }

        openPatientTabs={
          openPatientTabs
        }

        activePatientId={
          activePatientId
        }

        onSelectDashboard={
          handleSelectDashboard
        }

        onSelectPatientTab={
          handleSelectPatientTab
        }

        onClosePatientTab={
          handleClosePatientTab
        }
      />


      {/* =====================================================
          Workspace
          ===================================================== */}

      <div className="app-workspace">


        {/* Sidebar */}

        <Sidebar
          activeMenu={
            activeMenu
          }

          onMenuSelect={
            handleMenuSelect
          }
        />


        {/* Main Content */}

        <main className="app-content">

          {renderMainContent()}

        </main>


      </div>

    </div>

  );

}