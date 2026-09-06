import {
  useEffect,
  useRef,
  useState,
} from "react";

import type { Patient } from "../../features/patients/types";


/* =========================================================
   Props
   ========================================================= */

interface WorkspaceTabsProps {
  /**
   * Sidebar 접힘 여부
   *
   * false = 펼침
   * true  = 접힘
   */
  sidebarCollapsed?: boolean;


  /**
   * Hamburger 클릭
   */
  onToggleSidebar?: () => void;


  /**
   * 현재 열려 있는 환자 Chart 탭 목록
   *
   * 예:
   *
   * [
   *   김준수,
   *   이창섭
   * ]
   *
   * 화면:
   *
   * [Dashboard]
   * [김준수 | Chart ×]
   * [이창섭 | Chart ×]
   */
  openPatientTabs?: Patient[];


  /**
   * 현재 활성화된 환자의 id
   *
   * null
   * → Dashboard 활성
   *
   * patient id
   * → 해당 환자 Chart 탭 활성
   */
  activePatientId?: string | null;


  /**
   * Dashboard 탭 클릭
   */
  onSelectDashboard?: () => void;


  /**
   * 환자 Chart 탭 클릭
   */
  onSelectPatientTab?: (
    patientId: string,
  ) => void;


  /**
   * 환자 Chart 탭 닫기
   */
  onClosePatientTab?: (
    patientId: string,
  ) => void;
}


/* =========================================================
   WorkspaceTabs
   ========================================================= */

export default function WorkspaceTabs({
  sidebarCollapsed = false,

  onToggleSidebar = () => {},

  /*
   * 아직 AppShell에서 값을 전달하지 않아도
   * 오류가 나지 않도록 기본값 [] 사용
   */
  openPatientTabs = [],

  /*
   * null이면 Dashboard가 활성 상태
   */
  activePatientId = null,

  onSelectDashboard = () => {},

  onSelectPatientTab = () => {},

  onClosePatientTab = () => {},
}: WorkspaceTabsProps) {

  /* ========================================================
     1. 새 업무 메뉴 표시 여부
     ======================================================== */

  const [
    isNewWorkMenuOpen,
    setIsNewWorkMenuOpen,
  ] = useState(false);


  /* ========================================================
     2. 새 업무 메뉴 DOM 참조
     ======================================================== */

  const newWorkMenuRef =
    useRef<HTMLDivElement | null>(null);


  /* ========================================================
     3. + 버튼
     ======================================================== */

  const handleToggleNewWorkMenu = () => {
    setIsNewWorkMenuOpen(
      (previous) => !previous,
    );
  };


  /* ========================================================
     4. Popup 바깥 클릭
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


      /**
       * + 버튼 또는 Popup 내부 클릭
       *
       * → 닫지 않음
       */
      if (
        newWorkMenuRef.current?.contains(
          target,
        )
      ) {
        return;
      }


      /**
       * 그 외 영역 클릭
       *
       * → Popup 닫기
       */
      setIsNewWorkMenuOpen(false);
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
  }, [isNewWorkMenuOpen]);


  return (
    <div className="workspace-tabs">

      {/* =====================================================
          1. Hamburger
          ===================================================== */}

      <div className="workspace-tabs-sidebar-control">

        <button
          type="button"
          className="workspace-hamburger-button"

          onClick={onToggleSidebar}

          aria-expanded={!sidebarCollapsed}

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
          2. Workspace Tab 목록
          ===================================================== */}

      <div className="workspace-tabs-list">

        {/* ===================================================
            Dashboard

            activePatientId가 null일 때만
            Dashboard가 활성 상태가 된다.
            =================================================== */}

        <button
          type="button"

          className={
            activePatientId === null
              ? "workspace-tab active"
              : "workspace-tab"
          }

          onClick={onSelectDashboard}
        >
          <span className="workspace-tab-label">
            Dashboard
          </span>
        </button>


        {/* ===================================================
            3. 환자 Chart Tabs

            openPatientTabs에 들어있는 환자 수만큼
            자동으로 Tab을 만든다.

            환자 이름/번호는 API에서 온 값이며
            여기서 하드코딩하지 않는다.
            =================================================== */}

        {openPatientTabs.map(
          (patient) => {

            /**
             * 현재 환자 탭이
             * 활성 상태인지 확인
             */
            const isActive =
              activePatientId ===
              patient.id;


            return (
              <button
                key={patient.id}

                type="button"

                className={
                  isActive
                    ? "workspace-tab active"
                    : "workspace-tab"
                }

                /**
                 * 환자 탭 클릭
                 *
                 * → 해당 환자를 active로 변경
                 *
                 * 실제 상태 변경은
                 * 다음 단계 AppShell에서 처리한다.
                 */
                onClick={() =>
                  onSelectPatientTab(
                    patient.id,
                  )
                }
              >

                {/* 환자 이름 */}

                <span className="workspace-tab-label">
                  {patient.name}
                  {" | "}
                  Chart
                </span>


                {/* ===========================================
                    Tab 닫기

                    button 안에 별도 button을 넣으면
                    HTML 구조상 좋지 않기 때문에
                    span을 사용한다.

                    클릭 시 부모 Tab 클릭 이벤트가
                    같이 실행되지 않도록
                    stopPropagation() 처리.
                    =========================================== */}

                <span
                  className="workspace-tab-close"

                  role="button"

                  tabIndex={0}

                  aria-label={
                    `${patient.name} Chart 탭 닫기`
                  }

                  title="탭 닫기"

                  onClick={(event) => {
                    /**
                     * 환자 탭 자체 클릭 방지
                     */
                    event.stopPropagation();


                    onClosePatientTab(
                      patient.id,
                    );
                  }}

                  /**
                   * 키보드 접근성
                   *
                   * Enter / Space로도
                   * 탭을 닫을 수 있게 한다.
                   */
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
            4. 새 업무 +
            =================================================== */}

        <div
          className="workspace-new-work"

          ref={newWorkMenuRef}
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
              5. 새 업무 Popup
              ================================================= */}

          {isNewWorkMenuOpen && (

            <div className="workspace-new-work-menu">

              <div className="workspace-new-work-title">
                새 업무
              </div>


              {/*
               * 환자 검색은 제거.
               *
               * 이유:
               * Header의 통합 환자 검색이
               * 이미 환자 선택의 진입점이기 때문에
               * 같은 기능을 두 군데 만들지 않는다.
               */}


              {/* =============================================
                  영상 / 검사
                  ============================================= */}

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


              {/* =============================================
                  협진
                  ============================================= */}

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