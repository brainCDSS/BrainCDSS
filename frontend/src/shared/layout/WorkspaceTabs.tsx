import {
  useEffect,
  useRef,
  useState,
} from "react";

import type { Patient } from "../../features/patients/types";
import type { LoginUser } from "../../features/auth/types";

import type {
  ConsultationListItem,
} from "../../features/consultations/types";
import type { SidebarMenuKey } from "./Sidebar";
import { MENU_LABELS, canAccessMenu } from "./menuConfig";

export type MenuWorkspaceTabKey = Exclude<
  SidebarMenuKey,
  "dashboard" | "consultations"
>;

const NEW_WORK_GROUPS: Array<{
  label: string;
  items: Array<{
    key: Exclude<SidebarMenuKey, "dashboard">;
    icon: string;
  }>;
}> = [
  // [추가] 관리자 화면 연결
  {
    label: "관리자",
    items: [
      { key: "admin-users", icon: "관리" },
      { key: "admin-ml", icon: "ML" },
      { key: "admin-settings", icon: "설정" },
    ],
  },
  // [추가 끝] 관리자 화면 연결
  {
    label: "진료",
    items: [
      { key: "patients", icon: "○" },
      { key: "worklist", icon: "✓" },
      { key: "triage", icon: "✓" },
      { key: "clinical-notes", icon: "S" },
      { key: "appointments", icon: "□" },
    ],
  },
  {
    label: "검사 · 분석",
    items: [
      { key: "imaging", icon: "◇" },
      { key: "ai-results", icon: "◇" },
      { key: "radiology-reports", icon: "◇" },
      { key: "cdss", icon: "◇" },
    ],
  },
  {
    label: "협업",
    items: [
      { key: "consultations", icon: "◎" },
    ],
  },
  {
    label: "기타",
    items: [
      { key: "prescriptions", icon: "+" },
      { key: "notifications", icon: "!" },
    ],
  },
];


/* =========================================================
   Props
   ========================================================= */

interface WorkspaceTabsProps {
  currentUser: LoginUser;

  /* Sidebar */

  sidebarCollapsed?: boolean;

  onToggleSidebar?: () => void;

  /* Sidebar menu pages */

  openMenuTabs?: MenuWorkspaceTabKey[];

  activeMenu?: SidebarMenuKey;

  onSelectMenuTab?: (
    menu: MenuWorkspaceTabKey,
  ) => void;

  onCloseMenuTab?: (
    menu: MenuWorkspaceTabKey,
  ) => void;

  onOpenMenu?: (
    menu: SidebarMenuKey,
  ) => void;


  /* 일반 환자 */

  openPatientTabs?: Patient[];

  activePatientId?: string | null;

  onSelectPatientTab?: (
    patientId: string,
  ) => void;

  onClosePatientTab?: (
    patientId: string,
  ) => void;


  /* 협진 목록 */

  isConsultationListTabOpen?: boolean;

  isConsultationListActive?: boolean;

  onSelectConsultationListTab?: () => void;

  onCloseConsultationListTab?: () => void;


  /* 협진 Patient Review */

  openConsultationTabs?: ConsultationListItem[];

  activeConsultationId?: string | null;

  onSelectConsultationTab?: (
    consultationId: string,
  ) => void;

  onCloseConsultationTab?: (
    consultationId: string,
  ) => void;


  /* Dashboard */

  onSelectDashboard?: () => void;


  /* BrainOn AI */

  isAssistantTabOpen?: boolean;

  isAssistantTabActive?: boolean;

  onSelectAssistantTab?: () => void;

  onCloseAssistantTab?: () => void;

}


/* =========================================================
   WorkspaceTabs
   ========================================================= */

export default function WorkspaceTabs({
  currentUser,

  sidebarCollapsed = false,

  onToggleSidebar = () => {},

  openMenuTabs = [],

  activeMenu = "dashboard",

  onSelectMenuTab = () => {},

  onCloseMenuTab = () => {},

  onOpenMenu = () => {},


  /* 일반 환자 */

  openPatientTabs = [],

  activePatientId = null,

  onSelectPatientTab = () => {},

  onClosePatientTab = () => {},


  /* 협진 목록 */

  isConsultationListTabOpen = false,

  isConsultationListActive = false,

  onSelectConsultationListTab = () => {},

  onCloseConsultationListTab = () => {},


  /* 협진 */

  openConsultationTabs = [],

  activeConsultationId = null,

  onSelectConsultationTab = () => {},

  onCloseConsultationTab = () => {},


  /* Dashboard */

  onSelectDashboard = () => {},


  /* BrainOn AI */

  isAssistantTabOpen = false,

  isAssistantTabActive = false,

  onSelectAssistantTab = () => {},

  onCloseAssistantTab = () => {},

}: WorkspaceTabsProps) {

  const canOpenMenu = (menu: SidebarMenuKey) =>
    canAccessMenu(currentUser.role.code, menu);

  const visibleNewWorkGroups = NEW_WORK_GROUPS
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => canOpenMenu(item.key)),
    }))
    .filter((group) => group.items.length > 0);


  /* ========================================================
     1. 새 업무 Popup
     ======================================================== */

  const [
    isNewWorkMenuOpen,
    setIsNewWorkMenuOpen,
  ] = useState(false);


  /* ========================================================
     2. Popup DOM
     ======================================================== */

  const newWorkMenuRef =
    useRef<HTMLDivElement | null>(
      null,
    );


  /* ========================================================
     3. + 버튼
     ======================================================== */

  const handleToggleNewWorkMenu = () => {

    setIsNewWorkMenuOpen(
      (previous) => !previous,
    );

  };


  /* ========================================================
     4. Popup 외부 클릭
     ======================================================== */

  useEffect(() => {

    if (!isNewWorkMenuOpen) {
      return;
    }


    const handleOutsideClick = (
      event: MouseEvent,
    ) => {

      const target =
        event.target as Node;


      if (
        newWorkMenuRef.current?.contains(
          target,
        )
      ) {
        return;
      }


      setIsNewWorkMenuOpen(
        false,
      );

    };


    document.addEventListener(
      "mousedown",
      handleOutsideClick,
    );

    const handleEscape = (
      event: KeyboardEvent,
    ) => {

      if (event.key === "Escape") {
        setIsNewWorkMenuOpen(false);
      }

    };

    document.addEventListener(
      "keydown",
      handleEscape,
    );


    return () => {

      document.removeEventListener(
        "mousedown",
        handleOutsideClick,
      );

      document.removeEventListener(
        "keydown",
        handleEscape,
      );

    };

  }, [
    isNewWorkMenuOpen,
  ]);


  /* ========================================================
     5. Dashboard Active
     --------------------------------------------------------

     일반 환자 X
     협진 Patient Review X
     협진 목록 Active X

     → Dashboard 활성
     ======================================================== */

  const isDashboardActive =
    activeMenu === "dashboard" &&
    activePatientId === null &&
    activeConsultationId === null &&
    !isConsultationListActive &&
    !isAssistantTabActive;


  /* ========================================================
     Render
     ======================================================== */

  return (

    <div className="workspace-tabs">


      {/* =====================================================
          Hamburger
          ===================================================== */}

      <div className="workspace-tabs-sidebar-control">

        <button
          type="button"

          className="workspace-hamburger-button"

          onClick={
            onToggleSidebar
          }

          aria-expanded={
            !sidebarCollapsed
          }

          aria-label={
            sidebarCollapsed
              ? "사이드바 펼치기"
              : "사이드바 접기"
          }

          title={
            sidebarCollapsed
              ? "사이드바 펼치기"
              : "사이드바 접기"
          }
        >

          <span aria-hidden="true">
            ☰
          </span>

        </button>


      </div>


      {/* =====================================================
          Workspace Tabs
          ===================================================== */}

      <div className="workspace-tabs-list">

        {/* ===================================================
            Dashboard
            =================================================== */}

        <button
          type="button"

          className={
            isDashboardActive
              ? "workspace-tab workspace-tab--dashboard active"
              : "workspace-tab workspace-tab--dashboard"
          }

          onClick={
            onSelectDashboard
          }
        >

          <span className="workspace-tab-label">
            Dashboard
          </span>

        </button>


        <div className="workspace-tabs-scroll">


        {/* ===================================================
            BrainOn AI
            =================================================== */}

        {isAssistantTabOpen && (
          <button
            type="button"
            className={
              isAssistantTabActive
                ? "workspace-tab active"
                : "workspace-tab"
            }
            onClick={onSelectAssistantTab}
          >
            <span className="workspace-tab-label">
              BrainOn AI
            </span>

            <span
              className="workspace-tab-close"
              role="button"
              tabIndex={0}
              aria-label="BrainOn AI 탭 닫기"
              title="탭 닫기"
              onClick={(event) => {
                event.stopPropagation();
                onCloseAssistantTab();
              }}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" ||
                  event.key === " "
                ) {
                  event.preventDefault();
                  event.stopPropagation();
                  onCloseAssistantTab();
                }
              }}
            >
              ×
            </span>
          </button>
        )}


        {/* ===================================================
            Sidebar menu page Tabs
            =================================================== */}

        {openMenuTabs.filter(canOpenMenu).map((menu) => {

          const label = MENU_LABELS[menu];

          const isActive =
            activeMenu === menu &&
            activePatientId === null &&
            activeConsultationId === null;


          return (
            <button
              key={menu}
              type="button"
              className={
                isActive
                  ? "workspace-tab active"
                  : "workspace-tab"
              }
              onClick={() => {
                onSelectMenuTab(menu);
              }}
            >
              <span className="workspace-tab-label">
                {label}
              </span>

              <span
                className="workspace-tab-close"
                role="button"
                tabIndex={0}
                aria-label={`${label} 탭 닫기`}
                title="탭 닫기"
                onClick={(event) => {
                  event.stopPropagation();
                  onCloseMenuTab(menu);
                }}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" ||
                    event.key === " "
                  ) {
                    event.preventDefault();
                    event.stopPropagation();
                    onCloseMenuTab(menu);
                  }
                }}
              >
                ×
              </span>
            </button>
          );

        })}


        {/* ===================================================
            일반 환자 Chart Tabs
            =================================================== */}

        {openPatientTabs.map(
          (patient) => {

            const isActive =
              activePatientId ===
              patient.id;


            return (

              <button
                key={
                  `patient-chart:${patient.id}`
                }

                type="button"

                className={
                  isActive
                    ? "workspace-tab active"
                    : "workspace-tab"
                }

                onClick={() => {

                  onSelectPatientTab(
                    patient.id,
                  );

                }}
              >

                <span className="workspace-tab-label">

                  {patient.name} 차트

                </span>


                <span
                  className="workspace-tab-close"

                  role="button"

                  tabIndex={0}

                  aria-label={
                    `${patient.name} Chart 탭 닫기`
                  }

                  title="탭 닫기"

                  onClick={(event) => {

                    event.stopPropagation();


                    onClosePatientTab(
                      patient.id,
                    );

                  }}

                  onKeyDown={(event) => {

                    if (
                      event.key === "Enter" ||
                      event.key === " "
                    ) {

                      event.preventDefault();

                      event.stopPropagation();


                      onClosePatientTab(
                        patient.id,
                      );

                    }

                  }}
                >

                  ×

                </span>

              </button>

            );

          },
        )}


        {/* ===================================================
            협진 목록 Tab
            =================================================== */}

        {isConsultationListTabOpen && canOpenMenu("consultations") && (

          <button
            type="button"

            className={
              isConsultationListActive
                ? "workspace-tab active"
                : "workspace-tab"
            }

            onClick={
              onSelectConsultationListTab
            }
          >

            <span className="workspace-tab-label">

              협진 목록

            </span>


            <span
              className="workspace-tab-close"

              role="button"

              tabIndex={0}

              aria-label="협진 목록 탭 닫기"

              title="탭 닫기"

              onClick={(event) => {

                event.stopPropagation();


                onCloseConsultationListTab();

              }}

              onKeyDown={(event) => {

                if (
                  event.key === "Enter" ||
                  event.key === " "
                ) {

                  event.preventDefault();

                  event.stopPropagation();


                  onCloseConsultationListTab();

                }

              }}
            >

              ×

            </span>

          </button>

        )}


        {/* ===================================================
            협진 Patient Review Tabs
            =================================================== */}

        {canOpenMenu("consultations") && openConsultationTabs.map(
          (consultation) => {

            const consultationId =
              consultation.consultation_id;


            const patientName =
              consultation.patient_summary.name;


            const isActive =
              activeConsultationId ===
              consultationId;


            return (

              <button
                key={
                  consultationId
                }

                type="button"

                className={
                  isActive
                    ? "workspace-tab active"
                    : "workspace-tab"
                }

                onClick={() => {

                  onSelectConsultationTab(
                    consultationId,
                  );

                }}
              >

                <span className="workspace-tab-label">

                  협진 · {patientName}

                </span>


                <span
                  className="workspace-tab-close"

                  role="button"

                  tabIndex={0}

                  aria-label={
                    `${patientName} 협진 탭 닫기`
                  }

                  title="탭 닫기"

                  onClick={(event) => {

                    event.stopPropagation();


                    onCloseConsultationTab(
                      consultationId,
                    );

                  }}

                  onKeyDown={(event) => {

                    if (
                      event.key === "Enter" ||
                      event.key === " "
                    ) {

                      event.preventDefault();

                      event.stopPropagation();


                      onCloseConsultationTab(
                        consultationId,
                      );

                    }

                  }}
                >

                  ×

                </span>

              </button>

            );

          },
        )}

        </div>


        {/* ===================================================
            새 업무 +
            =================================================== */}

        <div
          className="workspace-new-work"

          ref={
            newWorkMenuRef
          }
        >

          <button
            type="button"

            className="workspace-add-tab-button"

            onClick={
              handleToggleNewWorkMenu
            }

            aria-expanded={
              isNewWorkMenuOpen
            }

            aria-label="새 업무 열기"

            title="새 업무 열기"
          >

            +

          </button>


          {/* =================================================
              새 업무 Popup
              ================================================= */}

          {isNewWorkMenuOpen && (

            <div className="workspace-new-work-menu">


              <div className="workspace-new-work-title">

                새 업무

              </div>


              {visibleNewWorkGroups.map((group) => (
                <div
                  className="workspace-new-work-group"
                  key={group.label}
                >
                  <div className="workspace-new-work-group-title">
                    {group.label}
                  </div>

                  {group.items.map((item) => (
                    <button
                      key={item.key}
                      type="button"
                      className="workspace-new-work-item"
                      onClick={() => {
                        if (!canOpenMenu(item.key)) return;
                        onOpenMenu(item.key);
                        setIsNewWorkMenuOpen(false);
                      }}
                    >
                      <span className="workspace-new-work-icon">
                        {item.icon}
                      </span>

                      <span>
                        {MENU_LABELS[item.key]}
                      </span>
                    </button>
                  ))}
                </div>
              ))}


            </div>

          )}


        </div>


      </div>


    </div>

  );

}
