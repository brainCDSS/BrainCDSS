import {
  useEffect,
  useRef,
  useState,
} from "react";

import type { Patient } from "../../features/patients/types";

import type {
  ConsultationListItem,
} from "../../features/consultations/types";


/* =========================================================
   Props
   ========================================================= */

interface WorkspaceTabsProps {

  /* Sidebar */

  sidebarCollapsed?: boolean;

  onToggleSidebar?: () => void;


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

}


/* =========================================================
   WorkspaceTabs
   ========================================================= */

export default function WorkspaceTabs({

  sidebarCollapsed = false,

  onToggleSidebar = () => {},


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

}: WorkspaceTabsProps) {


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


    return () => {

      document.removeEventListener(
        "mousedown",
        handleOutsideClick,
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
    activePatientId === null &&
    activeConsultationId === null &&
    !isConsultationListActive;


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
              ? "workspace-tab active"
              : "workspace-tab"
          }

          onClick={
            onSelectDashboard
          }
        >

          <span className="workspace-tab-label">
            Dashboard
          </span>

        </button>


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
                  patient.id
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

                  {patient.name}

                  {" | "}

                  Chart

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

        {isConsultationListTabOpen && (

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

        {openConsultationTabs.map(
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


              {/* 영상 / 검사 */}

              <button
                type="button"

                className="workspace-new-work-item"
              >

                <span className="workspace-new-work-icon">

                  I

                </span>


                <span>

                  영상 / 검사

                </span>

              </button>


              {/* 협진 */}

              <button
                type="button"

                className="workspace-new-work-item"
              >

                <span className="workspace-new-work-icon">

                  C

                </span>


                <span>

                  협진

                </span>

              </button>


            </div>

          )}


        </div>


      </div>


    </div>

  );

}