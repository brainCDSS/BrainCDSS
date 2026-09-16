import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";


//[추가 - 챗봇 플로팅 화면 연결]
import AssistantFloatingDock from "../../features/assistant/AssistantFloatingDock";
import AssistantWorkspace from "../../features/assistant/AssistantWorkspace";
import type { AssistantChatMessage } from "../../features/assistant/types";

import TriageAssessment from "../../features/assessments/TriageAssessment";
import ReceptionInitialAssessment from "../../features/assessments/ReceptionInitialAssessment";
// [추가] 신경과 응급 Worklist 연결
import EmergencyWorklist from "../../features/assessments/EmergencyWorklist";
// [추가 끝] 신경과 응급 Worklist 연결

import PatientChart from "../../features/patients/PatientChart";
import { getPatient } from "../../features/patients/api";

import ConsultationList from "../../features/consultations/ConsultationList";
import ConsultationPatientReview from "../../features/consultations/ConsultationPatientReview";
import { getConsultationDetail } from "../../features/consultations/api";
import ImagingPage from "../../features/imaging/ImagingPage";
import AIAnalysisResultsPage from "../../features/ai-analysis/AIAnalysisResultsPage";
import RadiologyReportsPage from "../../features/radiology/RadiologyReportsPage";
import CDSSResultsPage from "../../features/cdss/CDSSResultsPage";
import MedicationSafetyPage from "../../features/medication-safety/MedicationSafetyPage";
import { getActiveEncounter } from "../../features/medication-safety/api";
import NotificationsPage from "../../features/notifications/NotificationsPage";
import SurgicalPlanningPage from "../../features/surgical-planning/SurgicalPlanningPage";
import AppointmentsPage from "../../features/appointments/AppointmentsPage";
import ClinicalNotesPage from "../../features/clinical-notes/ClinicalNotesPage";

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

interface PrescriptionContext {
  patient: Patient;
  encounterId: string | null;
}

interface StoredWorkspaceState {
  userId: string;
  activeMenu: SidebarMenuKey;
  openMenuTabs: MenuWorkspaceTabKey[];
  activePatientId: string | null;
  openPatientIds: string[];
  activeConsultationId: string | null;
  openConsultationIds: string[];
  isConsultationListTabOpen: boolean;
  activeAssessmentContext: ActiveAssessmentContext | null;
  activeAnalysisId: string | null;
  isAssistantTabOpen: boolean;
  isAssistantTabActive: boolean;
  assistantPatientId: string | null;
}

const WORKSPACE_STORAGE_PREFIX = "brain-cdss-workspace";

const SIDEBAR_MENU_KEYS: SidebarMenuKey[] = [
  "dashboard", "patients", "worklist", "triage", "clinical-notes",
  "appointments", "imaging", "ai-results", "radiology-reports", "cdss",
  "consultations", "surgical-planning", "prescriptions", "notifications",
  "admin-users", "admin-monitoring", "admin-audit", "admin-settings",
];

function isSidebarMenuKey(value: unknown): value is SidebarMenuKey {
  return typeof value === "string" &&
    SIDEBAR_MENU_KEYS.includes(value as SidebarMenuKey);
}

function isMenuWorkspaceTabKey(value: unknown): value is MenuWorkspaceTabKey {
  return isSidebarMenuKey(value) &&
    value !== "dashboard" &&
    value !== "consultations";
}

function isStringOrNull(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function workspaceStorageKey(userId: string) {
  return `${WORKSPACE_STORAGE_PREFIX}:${userId}`;
}


/* =========================================================
   Brain CDSS AppShell
   ========================================================= */

export default function AppShell({
  children,
  currentUser,
  onLogout,
}: AppShellProps) {



  /* =======================================================
     0. 챗봇 플로팅
     ======================================================== */


  const [
    isAssistantFloatingOpen,
    setIsAssistantFloatingOpen,
  ] = useState(false);

  const [
    isAssistantTabOpen,
    setIsAssistantTabOpen,
  ] = useState(false);

  const [
    isAssistantTabActive,
    setIsAssistantTabActive,
  ] = useState(false);

  const [assistantMessages, setAssistantMessages] =
    useState<AssistantChatMessage[]>([]);
  const [assistantConversationId, setAssistantConversationId] =
    useState<string | null>(null);


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

  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null);


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

  const [
    assistantPatientId,
    setAssistantPatientId,
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

  const [prescriptionContext, setPrescriptionContext] =
    useState<PrescriptionContext | null>(null);
  const [patientEncounterIds, setPatientEncounterIds] = useState<
    Record<string, string | null>
  >({});
  const encounterRequestId = useRef(0);


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

  const [isWorkspaceHydrated, setIsWorkspaceHydrated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const storageKey = workspaceStorageKey(currentUser.id);

    async function restoreWorkspace() {
      try {
        const storedValue = sessionStorage.getItem(storageKey);
        if (!storedValue) return;

        const stored = JSON.parse(storedValue) as Partial<StoredWorkspaceState>;
        if (
          stored.userId !== currentUser.id ||
          !isSidebarMenuKey(stored.activeMenu) ||
          !canAccessMenu(currentUser.role.code, stored.activeMenu) ||
          !Array.isArray(stored.openMenuTabs) ||
          !Array.isArray(stored.openPatientIds) ||
          !Array.isArray(stored.openConsultationIds) ||
          !isStringOrNull(stored.activePatientId) ||
          !isStringOrNull(stored.activeConsultationId)
        ) {
          sessionStorage.removeItem(storageKey);
          return;
        }

        const openMenuTabs = stored.openMenuTabs.filter(
          (menu): menu is MenuWorkspaceTabKey =>
            isMenuWorkspaceTabKey(menu) &&
            canAccessMenu(currentUser.role.code, menu),
        );
        const patientIds = Array.from(new Set(
          stored.openPatientIds.filter(
            (id): id is string => typeof id === "string",
          ),
        ));
        const consultationIds = Array.from(new Set(
          stored.openConsultationIds.filter(
            (id): id is string => typeof id === "string",
          ),
        ));

        const [patientResults, consultationResults] = await Promise.all([
          canAccessMenu(currentUser.role.code, "patients")
            ? Promise.allSettled(patientIds.map((id) => getPatient(id)))
            : Promise.resolve([]),
          canAccessMenu(currentUser.role.code, "consultations")
            ? Promise.allSettled(
                consultationIds.map((id) => getConsultationDetail(id)),
              )
            : Promise.resolve([]),
        ]);
        if (cancelled) return;

        const patients = patientResults.flatMap((result) =>
          result.status === "fulfilled" ? [result.value] : [],
        );
        const consultations = consultationResults.flatMap((result) =>
          result.status === "fulfilled" ? [result.value] : [],
        );
        const restoredPatientId = patients.some(
          (patient) => patient.id === stored.activePatientId,
        ) ? stored.activePatientId : null;
        const restoredConsultationId = consultations.some(
          (consultation) =>
            consultation.consultation_id === stored.activeConsultationId,
        ) ? stored.activeConsultationId : null;
        const assessment = stored.activeAssessmentContext;
        const restoredAssessment =
          assessment &&
          typeof assessment.assessmentId === "string" &&
          typeof assessment.encounterId === "string" &&
          canAccessMenu(currentUser.role.code, "triage")
            ? assessment
            : null;
        const assistantIsActive =
          stored.isAssistantTabOpen === true &&
          stored.isAssistantTabActive === true;

        setOpenMenuTabs(openMenuTabs);
        setOpenPatientTabs(patients);
        setOpenConsultationTabs(consultations);
        setIsConsultationListTabOpen(
          stored.isConsultationListTabOpen === true &&
          canAccessMenu(currentUser.role.code, "consultations"),
        );
        setActiveAnalysisId(
          isStringOrNull(stored.activeAnalysisId)
            ? stored.activeAnalysisId
            : null,
        );
        setAssistantPatientId(
          isStringOrNull(stored.assistantPatientId)
            ? stored.assistantPatientId
            : null,
        );
        setIsAssistantTabOpen(stored.isAssistantTabOpen === true);
        setIsAssistantTabActive(assistantIsActive);

        if (assistantIsActive) {
          setActiveMenu("dashboard");
        } else if (restoredPatientId) {
          setActivePatientId(restoredPatientId);
          setActiveMenu("patients");
          const activePatient = patients.find(
            (patient) => patient.id === restoredPatientId,
          );
          if (activePatient) resolvePatientEncounter(activePatient);
        } else if (restoredConsultationId) {
          setActiveConsultationId(restoredConsultationId);
          setActiveMenu("consultations");
        } else if (stored.activeMenu === "triage") {
          if (restoredAssessment) {
            setActiveAssessmentContext(restoredAssessment);
            setActiveMenu("triage");
          }
        } else {
          setActiveMenu(stored.activeMenu);
        }
      } catch {
        sessionStorage.removeItem(storageKey);
      } finally {
        if (!cancelled) setIsWorkspaceHydrated(true);
      }
    }

    void restoreWorkspace();
    return () => {
      cancelled = true;
    };
  }, [currentUser.id, currentUser.role.code]);

  useEffect(() => {
    if (!isWorkspaceHydrated) return;

    const workspace: StoredWorkspaceState = {
      userId: currentUser.id,
      activeMenu,
      openMenuTabs,
      activePatientId,
      openPatientIds: openPatientTabs.map((patient) => patient.id),
      activeConsultationId,
      openConsultationIds: openConsultationTabs.map(
        (consultation) => consultation.consultation_id,
      ),
      isConsultationListTabOpen,
      activeAssessmentContext,
      activeAnalysisId,
      isAssistantTabOpen,
      isAssistantTabActive,
      assistantPatientId,
    };

    try {
      sessionStorage.setItem(
        workspaceStorageKey(currentUser.id),
        JSON.stringify(workspace),
      );
    } catch {
      // Storage 제한 환경에서는 현재 메모리 상태로 계속 동작한다.
    }
  }, [
    activeAnalysisId,
    activeAssessmentContext,
    activeConsultationId,
    activeMenu,
    activePatientId,
    assistantPatientId,
    currentUser.id,
    isAssistantTabActive,
    isAssistantTabOpen,
    isConsultationListTabOpen,
    isWorkspaceHydrated,
    openConsultationTabs,
    openMenuTabs,
    openPatientTabs,
  ]);


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

  function resolvePrescriptionEncounter(patient: Patient) {
    const requestId = ++encounterRequestId.current;
    setPrescriptionContext({ patient, encounterId: null });
    void getActiveEncounter(patient.id)
      .then((encounter) => {
        if (encounterRequestId.current !== requestId) return;
        setPrescriptionContext({
          patient,
          encounterId: encounter?.encounter_id ?? encounter?.id ?? null,
        });
      })
      .catch(() => {
        if (encounterRequestId.current === requestId) {
          setPrescriptionContext({ patient, encounterId: null });
        }
      });
  }

  function resolvePatientEncounter(patient: Patient) {
    const requestId = ++encounterRequestId.current;
    setPatientEncounterIds((current) => ({
      ...current,
      [patient.id]: null,
    }));
    setPrescriptionContext({ patient, encounterId: null });
    void getActiveEncounter(patient.id)
      .then((encounter) => {
        if (encounterRequestId.current !== requestId) return;
        const encounterId = encounter?.encounter_id ?? encounter?.id ?? null;
        setPatientEncounterIds((current) => ({
          ...current,
          [patient.id]: encounterId,
        }));
        setPrescriptionContext({ patient, encounterId });
      })
      .catch(() => {
        if (encounterRequestId.current !== requestId) return;
        setPatientEncounterIds((current) => ({
          ...current,
          [patient.id]: null,
        }));
        setPrescriptionContext({ patient, encounterId: null });
      });
  }


  /* ========================================================
     10. 현재 협진 목록 Tab 활성 여부
     ======================================================== */

  const isConsultationListActive =
    activeMenu === "consultations" &&
    activeConsultationId === null &&
    activePatientId === null;


  /* ========================================================
     BrainOn AI Workspace
     ======================================================== */

  const handleOpenAssistantWorkspace = () => {
    setAssistantPatientId(activePatientId);

    setIsAssistantTabOpen(true);
    setIsAssistantTabActive(true);
    setIsAssistantFloatingOpen(false);

    setActivePatientId(null);
    setActiveAssessmentContext(null);
    setActiveConsultationId(null);
    setActiveMenu("dashboard");
  };

  const handleSelectAssistantTab = () => {
    setAssistantPatientId(activePatientId);

    setIsAssistantTabActive(true);
    setIsAssistantFloatingOpen(false);

    setActivePatientId(null);
    setActiveAssessmentContext(null);
    setActiveConsultationId(null);
    setActiveMenu("dashboard");
  };

  const handleCloseAssistantTab = () => {
    setIsAssistantTabOpen(false);
    setIsAssistantTabActive(false);

    setActivePatientId(null);
    setActiveAssessmentContext(null);
    setActiveConsultationId(null);
    setActiveMenu("dashboard");
  };

  const handleMinimizeAssistantWorkspace = () => {
    setIsAssistantTabActive(false);
    setIsAssistantFloatingOpen(true);
    setActiveMenu("dashboard");
  };


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

    setIsAssistantTabActive(false);

    if (!canAccessMenu(currentUser.role.code, menu)) {
      return;
    }

    /* 환자 Chart에서 처방/DUR로 이동해도 선택 환자를 유지한다. */
    if (menu === "prescriptions" && activePatient) {
      resolvePrescriptionEncounter(activePatient);
    }

    /**
     * 현재 AppShell에서 실제 연결된 메뉴
     */
    if (
      menu !== "dashboard" &&
      menu !== "patients" &&
      menu !== "worklist" &&
      menu !== "triage" &&
      menu !== "clinical-notes" &&
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

    setIsAssistantTabActive(false);

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

    setIsAssistantTabActive(false);

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

    setIsAssistantTabActive(false);

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

    setIsAssistantTabActive(false);

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

    setIsAssistantTabActive(false);

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

    setIsAssistantTabActive(false);

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
    encounterId?: string,
  ) => {

    setIsAssistantTabActive(false);

    if (encounterId) {
      encounterRequestId.current += 1;
      setPatientEncounterIds((current) => ({
        ...current,
        [patient.id]: encounterId,
      }));
      setPrescriptionContext({ patient, encounterId });
    } else if (Object.prototype.hasOwnProperty.call(patientEncounterIds, patient.id)) {
      setPrescriptionContext({
        patient,
        encounterId: patientEncounterIds[patient.id],
      });
    } else {
      resolvePatientEncounter(patient);
    }

    setOpenPatientTabs(
      (current) =>
        current.some(
          (tab) => tab.id === patient.id,
        )
          ? current
          : [...current, patient],
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

  const handleWorklistPatientSelect = (
    patient: Patient,
    encounterId: string,
  ) => {
    handlePatientSelect(patient, encounterId);
  };

  const handleWorklistPrescriptionSelect = (
    patient: Patient,
    encounterId: string,
  ) => {
    setIsAssistantTabActive(false);
    setPrescriptionContext({ patient, encounterId });
    setActivePatientId(patient.id);
    setActiveAssessmentContext(null);
    setActiveConsultationId(null);
    setActiveMenu("prescriptions");
  };

  const handlePrescriptionPatientSelect = (patient: Patient) => {
    setIsAssistantTabActive(false);
    resolvePrescriptionEncounter(patient);
    setActivePatientId(null);
    setActiveAssessmentContext(null);
    setActiveConsultationId(null);
    setActiveMenu("prescriptions");
  };

  const handleOpenPrescriptionPatientChart = (patient: Patient) => {
    const encounterId =
      prescriptionContext?.patient.id === patient.id
        ? prescriptionContext.encounterId
        : null;
    setPatientEncounterIds((current) => ({
      ...current,
      [patient.id]: encounterId,
    }));
    setOpenPatientTabs((current) =>
      current.some((tab) => tab.id === patient.id) ? current : [...current, patient],
    );
    handleSelectPatientTab(patient.id);
  };


  /* ========================================================
     21. Dashboard Workspace Tab 선택
     ======================================================== */

  const handleSelectDashboard = () => {

    setIsAssistantTabActive(false);

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

    setIsAssistantTabActive(false);

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

    if (isAssistantTabActive) {
      return (
        <AssistantWorkspace
          patientId={assistantPatientId}
          messages={assistantMessages}
          setMessages={setAssistantMessages}
          conversationId={assistantConversationId}
          setConversationId={setAssistantConversationId}
          onMinimize={handleMinimizeAssistantWorkspace}
          onClose={handleCloseAssistantTab}
        />
      );
    }

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
          key="patient-chart"
          patient={
            activePatient
          }
          encounterId={patientEncounterIds[activePatient.id] ?? null}
          patients={
            openPatientTabs
          }
          canViewAIAnalyses={
            canAccessMenu(currentUser.role.code, "ai-results")
          }
          canViewConsultations={
            canAccessMenu(currentUser.role.code, "consultations")
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
          key="patient-chart"
          patient={null}
          encounterId={null}
          onSelectPatient={handlePatientSelect}
          onNavigate={handleMenuSelect}
          canViewAIAnalyses={
            canAccessMenu(currentUser.role.code, "ai-results")
          }
          canViewConsultations={
            canAccessMenu(currentUser.role.code, "consultations")
          }
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
      // [추가] 신경과 응급 Worklist 연결
      return (
        <EmergencyWorklist
          onOpenPatient={handleWorklistPatientSelect}
          onOpenPrescription={
            canAccessMenu(currentUser.role.code, "prescriptions")
              ? handleWorklistPrescriptionSelect
              : undefined
          }
        />
      );
      // [추가 끝] 신경과 응급 Worklist 연결

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
      /* ========================================================
        Triage 완료 → 접수 화면
        ======================================================== */

      const handleTriageComplete = () => {
        setActiveAssessmentContext(
          null,
        );

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

          onComplete={
            handleTriageComplete
          }
        />
      );

    }

    if (activeMenu === "appointments") {
      return <AppointmentsPage currentUser={currentUser} />;
    }

    if (activeMenu === "clinical-notes") {
      return <ClinicalNotesPage />;
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

      return <ImagingPage onAnalysisStarted={(analysis) => {
        setActiveAnalysisId(analysis.analysis_id);
        handleMenuSelect("ai-results");
      }} />;

    }

    if (activeMenu === "ai-results") {
      return <AIAnalysisResultsPage initialAnalysisId={activeAnalysisId} />;
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
      return (
        <MedicationSafetyPage
          context={prescriptionContext === null ? null : {
            patient: prescriptionContext.patient,
            encounterId: prescriptionContext.encounterId,
          }}
          onSelectPatient={handlePrescriptionPatientSelect}
          onOpenPatientChart={handleOpenPrescriptionPatientChart}
        />
      );
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

  if (!isWorkspaceHydrated) {
    return (
      <div className="workspace-loading">
        <div className="brainon-loading__visual">
          <img
            src="/loading-brain.png"
            alt="Brain On"
            className="brainon-loading__image"
          />
          <div className="brainon-loading__text">페이지를 불러오는 중입니다...</div>
          <div
            className="brainon-loading__spinner"
            role="status"
            aria-label="화면 로딩 중"
          />
        </div>
      </div>
    );
  }

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


        /* BrainOn AI */

        isAssistantTabOpen={
          isAssistantTabOpen
        }

        isAssistantTabActive={
          isAssistantTabActive
        }

        onSelectAssistantTab={
          handleSelectAssistantTab
        }

        onCloseAssistantTab={
          handleCloseAssistantTab
        }

      />


      {/* =====================================================
          Workspace
          ===================================================== */}

      <div className="app-workspace">


        {/* Sidebar */}

        <Sidebar
          currentUser={currentUser}
          activeMenu={activeMenu}
          onMenuSelect={handleMenuSelect}
        />


        {/* Main Content */}

        <main className="app-content">

          {renderMainContent()}

        </main>
      </div>

      <AssistantFloatingDock
        isOpen={isAssistantFloatingOpen}
        patientId={activePatientId}
        messages={assistantMessages}
        setMessages={setAssistantMessages}
        conversationId={assistantConversationId}
        setConversationId={setAssistantConversationId}
        onToggle={() => {
          setIsAssistantFloatingOpen(
            (previous) => !previous,
          );
        }}
        onExpand={
          handleOpenAssistantWorkspace
        }
        onClose={() => {
          setIsAssistantFloatingOpen(false);
        }}
      />

    </div>

  );

}
