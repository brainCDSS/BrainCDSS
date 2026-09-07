import { useState } from "react";
import type { ReactNode } from "react";

import AssessmentWorklist from "../../features/assessments/AssessmentWorklist";
import TriageAssessment from "../../features/assessments/TriageAssessment";

import PatientChart from "../../features/patients/PatientChart";

import ConsultationList from "../../features/consultations/ConsultationList";
import ConsultationPatientReview from "../../features/consultations/ConsultationPatientReview";

import type { Patient } from "../../features/patients/types";
import type { ConsultationListItem } from "../../features/consultations/types";
import type { SidebarMenuKey } from "./Sidebar";

import Header from "./Header";
import Sidebar from "./Sidebar";
import WorkspaceTabs from "./WorkspaceTabs";

import "./layout.css";


/* =========================================================
   Props
   ========================================================= */

interface AppShellProps {
  children: ReactNode;
}


/* =========================================================
   현재 진행 중인 Triage Context
   ========================================================= */

interface ActiveAssessmentContext {
  assessmentId: string;
  encounterId: string;
}


/* =========================================================
   Brain CDSS 공통 Layout
   ========================================================= */

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
     3. 현재 열려 있는 일반 환자 Tabs
     ======================================================== */

  const [
    openPatientTabs,
    setOpenPatientTabs,
  ] = useState<Patient[]>([]);


  /* ========================================================
     4. 현재 활성 일반 환자
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
     6. 현재 보고 있는 협진
     --------------------------------------------------------

     null
     → 협진 목록

     consultation_id
     → 해당 Consultation Patient Review
     ======================================================== */

  const [
    activeConsultationId,
    setActiveConsultationId,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     7. 현재 활성 일반 환자 객체
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
     * 현재 실제 Content가 연결된 메뉴만 허용
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
     * Sidebar 메뉴로 이동하면
     * 일반 환자 Chart 비활성화
     */
    setActivePatientId(
      null,
    );


    /**
     * Triage 이외 화면으로 이동하면
     * Assessment Context 해제
     */
    if (menu !== "triage") {

      setActiveAssessmentContext(
        null,
      );

    }


    /**
     * 협진 목록을 Sidebar에서 직접 누른 경우
     *
     * 현재 Patient Review를 종료하고
     * 협진 목록부터 표시한다.
     */
    if (menu === "consultations") {

      setActiveConsultationId(
        null,
      );

    }


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


    setActiveMenu(
      "triage",
    );

  };


  /* ========================================================
     11. 협진 목록 → Patient Review
     --------------------------------------------------------

     [검토하기]

     ConsultationListItem
     ↓
     consultation_id 저장
     ↓
     Patient Review 표시
     ======================================================== */

  const handleOpenConsultationReview = (
    consultation: ConsultationListItem,
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
      consultation.consultation_id,
    );


    /**
     * Sidebar에서는 여전히
     * 협진 업무 영역으로 처리
     */
    setActiveMenu(
      "consultations",
    );

  };


  /* ========================================================
     12. Patient Review → 협진 목록
     ======================================================== */

  const handleBackToConsultationList = () => {

    /**
     * 현재 협진 상세 선택 해제
     */
    setActiveConsultationId(
      null,
    );


    setActiveMenu(
      "consultations",
    );

  };


  /* ========================================================
     13. Header에서 일반 환자 선택
     ======================================================== */

  const handlePatientSelect = (
    patient: Patient,
  ) => {

    /**
     * 이미 열려 있는 환자는
     * 중복 Tab 생성하지 않음
     */
    setOpenPatientTabs(
      (previousTabs) => {

        const alreadyOpen =
          previousTabs.some(
            (openedPatient) =>
              openedPatient.id ===
              patient.id,
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


    /**
     * 일반 환자 Chart 활성화
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


    setActiveMenu(
      "dashboard",
    );

  };


  /* ========================================================
     15. 일반 환자 Workspace Tab 선택
     ======================================================== */

  const handleSelectPatientTab = (
    patientId: string,
  ) => {

    setActiveAssessmentContext(
      null,
    );


    setActivePatientId(
      patientId,
    );

  };


  /* ========================================================
     16. 일반 환자 Workspace Tab 닫기
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


    /**
     * 현재 보고 있던 환자 Tab을 닫은 경우
     * Dashboard로 이동
     */
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
     17. Main Content
     ======================================================== */

  function renderMainContent() {


    /* -------------------------------------------------------
       일반 환자 Chart
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
       --------------------------------------------------------

       activeConsultationId 있음
       → Patient Review

       activeConsultationId 없음
       → 협진 목록
       ------------------------------------------------------- */

    if (activeMenu === "consultations") {

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