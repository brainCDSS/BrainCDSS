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
   Brain CDSS AppShell
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
     3. 일반 환자 Workspace Tabs
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
     6. 현재 활성 협진
     --------------------------------------------------------

     null
     → 협진 목록

     consultation_id
     → 해당 협진 Patient Review
     ======================================================== */

  const [
    activeConsultationId,
    setActiveConsultationId,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     7. 협진 환자 Workspace Tabs
     ======================================================== */

  const [
    openConsultationTabs,
    setOpenConsultationTabs,
  ] = useState<ConsultationListItem[]>([]);


  /* ========================================================
     8. 협진 목록 Workspace Tab 열림 여부
     ======================================================== */

  const [
    isConsultationListTabOpen,
    setIsConsultationListTabOpen,
  ] = useState(false);


  /* ========================================================
     9. 현재 활성 일반 환자 객체
     ======================================================== */

  const activePatient =
    activePatientId === null
      ? null
      : openPatientTabs.find(
          (patient) =>
            patient.id === activePatientId,
        ) ?? null;


  /* ========================================================
     10. 현재 협진 목록 Tab 활성 여부
     ======================================================== */

  const isConsultationListActive =
    activeMenu === "consultations" &&
    activeConsultationId === null &&
    activePatientId === null;


  /* ========================================================
     11. Sidebar 접기 / 펼치기
     ======================================================== */

  const handleToggleSidebar = () => {

    setSidebarCollapsed(
      (previous) => !previous,
    );

  };


  /* ========================================================
     12. Sidebar 메뉴 선택
     ======================================================== */

  const handleMenuSelect = (
    menu: SidebarMenuKey,
  ) => {

    /**
     * 현재 AppShell에서 실제 연결된 메뉴
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
     * 일반 환자 비활성
     */
    setActivePatientId(
      null,
    );


    /**
     * 특정 협진 Patient Review 비활성
     */
    setActiveConsultationId(
      null,
    );


    /**
     * Triage 이외 화면 이동 시
     * Assessment Context 해제
     */
    if (menu !== "triage") {

      setActiveAssessmentContext(
        null,
      );

    }


    /**
     * Sidebar에서 협진 목록 선택
     *
     * 협진 목록 Workspace Tab 생성
     */
    if (menu === "consultations") {

      setIsConsultationListTabOpen(
        true,
      );

    }


    setActiveMenu(
      menu,
    );

  };


  /* ========================================================
     13. Worklist → Triage
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
     14. 협진 목록 → Patient Review
     ======================================================== */

  const handleOpenConsultationReview = (
    consultation: ConsultationListItem,
  ) => {

    /**
     * 일반 환자 비활성
     */
    setActivePatientId(
      null,
    );


    /**
     * Triage Context 비활성
     */
    setActiveAssessmentContext(
      null,
    );


    /**
     * 협진 목록에서 들어온 것이므로
     * 협진 목록 Tab도 열린 상태 유지
     */
    setIsConsultationListTabOpen(
      true,
    );


    /**
     * 협진 Patient Review Tab 추가
     *
     * 같은 consultation_id는
     * 중복으로 생성하지 않는다.
     */
    setOpenConsultationTabs(
      (previousTabs) => {

        const alreadyOpen =
          previousTabs.some(
            (openedConsultation) =>
              openedConsultation.consultation_id ===
              consultation.consultation_id,
          );


        if (alreadyOpen) {
          return previousTabs;
        }


        return [
          ...previousTabs,
          consultation,
        ];

      },
    );


    /**
     * 선택 협진 활성화
     */
    setActiveConsultationId(
      consultation.consultation_id,
    );


    setActiveMenu(
      "consultations",
    );

  };


  /* ========================================================
     15. Patient Review → 협진 목록
     ======================================================== */

  const handleBackToConsultationList = () => {

    /**
     * 협진 목록 Tab 생성 / 유지
     */
    setIsConsultationListTabOpen(
      true,
    );


    /**
     * 특정 협진 Patient Review 비활성
     */
    setActiveConsultationId(
      null,
    );


    /**
     * 일반 환자 비활성
     */
    setActivePatientId(
      null,
    );


    setActiveMenu(
      "consultations",
    );

  };


  /* ========================================================
     16. 협진 목록 Workspace Tab 선택
     ======================================================== */

  const handleSelectConsultationListTab = () => {

    setActivePatientId(
      null,
    );


    setActiveAssessmentContext(
      null,
    );


    /**
     * 특정 협진 Patient Review 비활성
     */
    setActiveConsultationId(
      null,
    );


    setActiveMenu(
      "consultations",
    );

  };


  /* ========================================================
     17. 협진 목록 Workspace Tab 닫기
     ======================================================== */

  const handleCloseConsultationListTab = () => {

    /**
     * 목록 Tab 제거
     */
    setIsConsultationListTabOpen(
      false,
    );


    /**
     * 현재 보고 있던 화면이
     * 협진 목록이라면 Dashboard 이동
     */
    if (isConsultationListActive) {

      setActiveConsultationId(
        null,
      );


      setActiveMenu(
        "dashboard",
      );

    }

  };


  /* ========================================================
     18. 협진 Patient Review Tab 선택
     ======================================================== */

  const handleSelectConsultationTab = (
    consultationId: string,
  ) => {

    setActivePatientId(
      null,
    );


    setActiveAssessmentContext(
      null,
    );


    setActiveConsultationId(
      consultationId,
    );


    setActiveMenu(
      "consultations",
    );

  };


  /* ========================================================
     19. 협진 Patient Review Tab 닫기
     ======================================================== */

  const handleCloseConsultationTab = (
    consultationId: string,
  ) => {

    /**
     * 열린 협진 Tab 목록에서 제거
     */
    setOpenConsultationTabs(
      (previousTabs) =>
        previousTabs.filter(
          (consultation) =>
            consultation.consultation_id !==
            consultationId,
        ),
    );


    /**
     * 현재 활성 협진을 닫은 경우
     *
     * 협진 목록 Tab이 열려 있으면
     * 협진 목록으로 이동
     *
     * 목록 Tab도 없다면 Dashboard
     */
    if (
      activeConsultationId ===
      consultationId
    ) {

      setActiveConsultationId(
        null,
      );


      if (isConsultationListTabOpen) {

        setActiveMenu(
          "consultations",
        );

      } else {

        setActiveMenu(
          "dashboard",
        );

      }

    }

  };


  /* ========================================================
     20. Header에서 일반 환자 선택
     ======================================================== */

  const handlePatientSelect = (
    patient: Patient,
  ) => {

    /**
     * 동일 환자 중복 Tab 방지
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


    setActiveAssessmentContext(
      null,
    );


    /**
     * 협진 상세 비활성
     *
     * 협진 Tabs 자체는 유지
     */
    setActiveConsultationId(
      null,
    );


    setActivePatientId(
      patient.id,
    );

  };


  /* ========================================================
     21. Dashboard Workspace Tab 선택
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
     22. 일반 환자 Workspace Tab 선택
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
     23. 일반 환자 Workspace Tab 닫기
     ======================================================== */

  const handleClosePatientTab = (
    patientId: string,
  ) => {

    setOpenPatientTabs(
      (previousTabs) =>
        previousTabs.filter(
          (patient) =>
            patient.id !==
            patientId,
        ),
    );


    if (
      activePatientId ===
      patientId
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
     24. Main Content
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

    if (
      activeMenu ===
      "worklist"
    ) {

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

    if (
      activeMenu ===
      "triage"
    ) {

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

       activeConsultationId 있음
       → Patient Review

       activeConsultationId 없음
       → ConsultationList
       ------------------------------------------------------- */

    if (
      activeMenu ===
      "consultations"
    ) {

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
       Dashboard
       ------------------------------------------------------- */

    return children;

  }


  /* ========================================================
     25. Layout
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


        /* 일반 환자 */

        openPatientTabs={
          openPatientTabs
        }

        activePatientId={
          activePatientId
        }

        onSelectPatientTab={
          handleSelectPatientTab
        }

        onClosePatientTab={
          handleClosePatientTab
        }


        /* 협진 목록 */

        isConsultationListTabOpen={
          isConsultationListTabOpen
        }

        isConsultationListActive={
          isConsultationListActive
        }

        onSelectConsultationListTab={
          handleSelectConsultationListTab
        }

        onCloseConsultationListTab={
          handleCloseConsultationListTab
        }


        /* 협진 Patient Review */

        openConsultationTabs={
          openConsultationTabs
        }

        activeConsultationId={
          activeConsultationId
        }

        onSelectConsultationTab={
          handleSelectConsultationTab
        }

        onCloseConsultationTab={
          handleCloseConsultationTab
        }


        /* Dashboard */

        onSelectDashboard={
          handleSelectDashboard
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