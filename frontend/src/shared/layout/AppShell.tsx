import { useState } from "react";
import type { ReactNode } from "react";

import TriageAssessment from "../../features/assessments/TriageAssessment";
import ReceptionInitialAssessment from "../../features/assessments/ReceptionInitialAssessment";

import PatientChart from "../../features/patients/PatientChart";

import ConsultationList from "../../features/consultations/ConsultationList";
import ConsultationPatientReview from "../../features/consultations/ConsultationPatientReview";
import ImagingPage from "../../features/imaging/ImagingPage";
import AIAnalysisResultsPage from "../../features/ai-analysis/AIAnalysisResultsPage";
import RadiologyReportsPage from "../../features/radiology/RadiologyReportsPage";
import CDSSResultsPage from "../../features/cdss/CDSSResultsPage";
import MedicationSafetyPage from "../../features/medication-safety/MedicationSafetyPage";
import NotificationsPage from "../../features/notifications/NotificationsPage";
import SurgicalPlanningPage from "../../features/surgical-planning/SurgicalPlanningPage";
import AppointmentsPage from "../../features/appointments/AppointmentsPage";
// [추가] 관리자 화면 연결
import AdminDashboard from "../../features/admin/AdminDashboard";
import AdminUsersPage from "../../features/admin/AdminUsersPage";
import SystemMonitoringPage from "../../features/admin/SystemMonitoringPage";
import AuditLogPage from "../../features/admin/AuditLogPage";
import AdminSettingsPage from "../../features/admin/AdminSettingsPage";
// [추가 끝] 관리자 화면 연결

import type { Patient } from "../../features/patients/types";
import type { ConsultationListItem } from "../../features/consultations/types";
import type { LoginUser } from "../../features/auth/types";
import type { SidebarMenuKey } from "./Sidebar";

import Header from "./Header";
import Sidebar from "./Sidebar";
import WorkspaceTabs from "./WorkspaceTabs";
import type { MenuWorkspaceTabKey } from "./WorkspaceTabs";
import { canAccessMenu } from "./menuConfig";

import "./layout.css";


/* =========================================================
   Props
   ========================================================= */

interface AppShellProps {
  children: ReactNode | ((
    onOpenPatient: (patient: Patient) => void,
    onOpenMenu: (menu: SidebarMenuKey) => void,
  ) => ReactNode);
  currentUser: LoginUser;
  onLogout: () => void;
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
  currentUser,
  onLogout,
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
     9. Sidebar menu Workspace Tabs
     ======================================================== */

  const [
    openMenuTabs,
    setOpenMenuTabs,
  ] = useState<MenuWorkspaceTabKey[]>([]);


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

    if (!canAccessMenu(currentUser.role.code, menu)) {
      return;
    }

    /**
     * 현재 AppShell에서 실제 연결된 메뉴
     */
    if (
      menu !== "dashboard" &&
      menu !== "patients" &&
      menu !== "worklist" &&
      menu !== "triage" &&
      menu !== "appointments" &&
      menu !== "consultations" &&
      menu !== "imaging" &&
      menu !== "ai-results" &&
      menu !== "radiology-reports" &&
      menu !== "cdss" &&
      menu !== "surgical-planning" &&
      menu !== "prescriptions" &&
      menu !== "notifications" &&
      // [추가] 관리자 화면 연결
      menu !== "admin-users" &&
      menu !== "admin-monitoring" &&
      menu !== "admin-audit" &&
      menu !== "admin-settings"
      // [추가 끝] 관리자 화면 연결
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


    if (
      menu !== "dashboard" &&
      menu !== "consultations"
    ) {

      setOpenMenuTabs(
        (previousTabs) =>
          previousTabs.includes(menu)
            ? previousTabs
            : [...previousTabs, menu],
      );

    }


    setActiveMenu(
      menu,
    );

  };


  /* ========================================================
     Sidebar menu Workspace Tab 선택 / 닫기
     ======================================================== */

  const handleSelectMenuTab = (
    menu: MenuWorkspaceTabKey,
  ) => {

    if (!canAccessMenu(currentUser.role.code, menu)) {
      return;
    }

    setActivePatientId(null);
    setActiveConsultationId(null);

    if (menu !== "triage") {
      setActiveAssessmentContext(null);
    }

    setActiveMenu(menu);

  };


  const handleCloseMenuTab = (
    menu: MenuWorkspaceTabKey,
  ) => {

    const closedIndex =
      openMenuTabs.indexOf(menu);

    const remainingTabs =
      openMenuTabs.filter(
        (openedMenu) => openedMenu !== menu,
      );

    setOpenMenuTabs(remainingTabs);

    const isClosingActiveMenu =
      activeMenu === menu &&
      activePatientId === null &&
      activeConsultationId === null;

    if (!isClosingActiveMenu) {
      return;
    }

    const adjacentMenu =
      remainingTabs[
        Math.min(
          closedIndex,
          remainingTabs.length - 1,
        )
      ];

    if (adjacentMenu) {
      handleSelectMenuTab(adjacentMenu);
      return;
    }

    if (isConsultationListTabOpen) {
      handleSelectConsultationListTab();
      return;
    }

    handleSelectDashboard();

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

      const adjacentMenu =
        openMenuTabs[openMenuTabs.length - 1];

      if (adjacentMenu) {
        handleSelectMenuTab(adjacentMenu);
      } else {
        setActiveMenu(
          "dashboard",
        );
      }

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

        const adjacentMenu =
          openMenuTabs[openMenuTabs.length - 1];

        if (adjacentMenu) {
          handleSelectMenuTab(adjacentMenu);
        } else {
          setActiveMenu(
            "dashboard",
          );
        }

      }

    }

  };


  /* ========================================================
     20. Header에서 일반 환자 선택
     ======================================================== */

  const handlePatientSelect = (
    patient: Patient,
  ) => {

    /* patient.id별 차트 탭을 유지하고, 같은 환자는 기존 탭을 재사용한다. */
    setOpenPatientTabs(
      (previousTabs) => {
        const existingIndex = previousTabs.findIndex(
          (openedPatient) => openedPatient.id === patient.id,
        );

        if (existingIndex === -1) {
          return [...previousTabs, patient];
        }

        return previousTabs.map(
          (openedPatient, index) =>
            index === existingIndex ? patient : openedPatient,
        );
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


    setActiveMenu(
      "patients",
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


    setActiveMenu(
      "patients",
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
          (patient) => patient.id !== patientId,
        ),
    );

    handleSelectDashboard();

  };


  /* ========================================================
     24. Main Content
     ======================================================== */

  function renderMainContent() {

    const requestedMenu = activePatient ? "patients" : activeMenu;
    if (!canAccessMenu(currentUser.role.code, requestedMenu)) {
      return (
        <section className="clinical-page">
          <div className="clinical-card">
            <div className="clinical-state">
              현재 로그인 역할로 접근할 수 없는 업무입니다.
            </div>
          </div>
        </section>
      );
    }

    // [추가] 관리자 화면 연결
    if (currentUser.role.code === "SYSTEM_ADMIN") {
      if (activeMenu === "admin-users") return <AdminUsersPage />;
      if (activeMenu === "admin-monitoring") return <SystemMonitoringPage />;
      if (activeMenu === "admin-audit") return <AuditLogPage />;
      if (activeMenu === "admin-settings") return <AdminSettingsPage />;
      return <AdminDashboard />;
    }
    // [추가 끝] 관리자 화면 연결


    /* -------------------------------------------------------
       일반 환자 Chart
       ------------------------------------------------------- */

    if (activePatient) {

      return (
        <PatientChart
          key={`patient-chart:${activePatient.id}`}
          patient={
            activePatient
          }
          patients={
            openPatientTabs
          }
          onSelectPatient={
            handlePatientSelect
          }
          onNavigate={
            handleMenuSelect
          }
        />
      );

    }


    /* -------------------------------------------------------
       환자 관리
       ------------------------------------------------------- */

    if (
      activeMenu === "patients"
    ) {

      return (
        <PatientChart
          key="patient-management"
          patient={null}
          onSelectPatient={handlePatientSelect}
          onNavigate={handleMenuSelect}
        />
      );

    }


    /* -------------------------------------------------------
       신경과 응급 Worklist

       GET /api/v1/neurology/emergency-worklist 전용 화면은
       아직 구현되지 않았으므로 초기평가 Worklist를 대신 연결하지 않는다.
       ------------------------------------------------------- */

    if (
      activeMenu ===
      "worklist"
    ) {

      return (
        <section className="clinical-page">
          <header className="clinical-page__heading">
            <h2>응급 Worklist</h2>
            <p>
              Triage 완료 후 긴급·응급으로 분류된 환자를
              신경과 의료진이 확인하는 업무 화면입니다.
            </p>
          </header>

          <div className="clinical-card">
            <div className="clinical-state">
              신경과 응급 Worklist API 화면은 아직 구현되지 않았습니다.
            </div>
          </div>
        </section>
      );

    }


    /* -------------------------------------------------------
       접수 · 초기평가

       Assessment가 선택되기 전에는 초기평가 대기목록을 표시하고,
       대기목록에서 Triage를 시작하면 기존 입력 화면으로 이어진다.
       ------------------------------------------------------- */

    if (
      activeMenu ===
      "triage"
    ) {

      if (!activeAssessmentContext) {

        return (
          <ReceptionInitialAssessment
            onOpenTriage={
              handleOpenTriage
            }
          />
        );

      }


      const triageKey =
        `${activeAssessmentContext.assessmentId}:${activeAssessmentContext.encounterId}`;


      return (
        <TriageAssessment
          key={
            triageKey
          }

          assessmentId={
            activeAssessmentContext.assessmentId
          }

          encounterId={
            activeAssessmentContext.encounterId
          }
        />
      );

    }

    if (activeMenu === "appointments") {
      return <AppointmentsPage currentUser={currentUser} />;
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
       검사 / 영상
       ------------------------------------------------------- */

    if (
      activeMenu ===
      "imaging"
    ) {

      return <ImagingPage />;

    }

    if (activeMenu === "ai-results") {
      return <AIAnalysisResultsPage />;
    }

    if (activeMenu === "radiology-reports") {
      return <RadiologyReportsPage />;
    }

    if (activeMenu === "cdss") {
      return <CDSSResultsPage />;
    }

    if (activeMenu === "surgical-planning") {
      return <SurgicalPlanningPage />;
    }

    if (activeMenu === "prescriptions") {
      return <MedicationSafetyPage />;
    }

    if (activeMenu === "notifications") {
      return <NotificationsPage />;
    }


    /* -------------------------------------------------------
       Dashboard
       ------------------------------------------------------- */

    return typeof children === "function"
      ? children(handlePatientSelect, handleMenuSelect)
      : children;

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
        currentUser={currentUser}
        onLogout={onLogout}
      />


      {/* =====================================================
          Workspace Tabs
          ===================================================== */}

      <WorkspaceTabs
        currentUser={currentUser}

        sidebarCollapsed={
          sidebarCollapsed
        }

        onToggleSidebar={
          handleToggleSidebar
        }

        openMenuTabs={
          openMenuTabs
        }

        activeMenu={
          activeMenu
        }

        onSelectMenuTab={
          handleSelectMenuTab
        }

        onCloseMenuTab={
          handleCloseMenuTab
        }

        onOpenMenu={
          handleMenuSelect
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
          currentUser={currentUser}
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
