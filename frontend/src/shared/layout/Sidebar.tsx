import {
  useEffect,
  useState,
} from "react";

import "./layout.css";


/* =========================================================
   Sidebar Menu Key
   ---------------------------------------------------------
   실제 화면을 식별하는 key

   추후 역할별 권한을 적용할 때도
   이 key 기준으로 메뉴 노출 여부를 제어한다.
   ========================================================= */

export type SidebarMenuKey =
  | "dashboard"
  | "patients"

  | "worklist"
  | "triage"

  | "imaging"
  | "ai-results"
  | "radiology-reports"
  | "cdss"

  | "consultations"
  | "surgical-planning"

  | "prescriptions"
  | "notifications";


/* =========================================================
   Sidebar Group Key
   ========================================================= */

type SidebarGroupKey =
  | "clinical"
  | "analysis"
  | "consultation";


/* =========================================================
   Sidebar Props
   ========================================================= */

interface SidebarProps {
  activeMenu?: SidebarMenuKey;

  onMenuSelect?: (
    menu: SidebarMenuKey,
  ) => void;
}


/* =========================================================
   단일 메뉴
   ========================================================= */

interface SidebarSingleMenu {
  type: "single";

  key: SidebarMenuKey;

  label: string;

  icon: string;
}


/* =========================================================
   2Depth 메뉴
   ========================================================= */

interface SidebarChildMenu {
  key: SidebarMenuKey;

  label: string;
}


interface SidebarGroupMenu {
  type: "group";

  key: SidebarGroupKey;

  label: string;

  icon: string;

  children: SidebarChildMenu[];
}


type SidebarMenuItem =
  | SidebarSingleMenu
  | SidebarGroupMenu;


/* =========================================================
   Sidebar Menu Structure
   ---------------------------------------------------------
   CLINICAL WORKSPACE

   Dashboard
   환자 관리

   진료 업무
     - Worklist
     - 접수 / Triage

   검사 · 분석
     - 검사 / 영상
     - AI 분석 결과
     - 최종 판독
     - CDSS 결과

   협진
     - 협진 목록
     - 수술 · 시술 플래닝

   처방 / DUR
   알림 센터
   ========================================================= */

const menuItems: SidebarMenuItem[] = [

  /* -------------------------------------------------------
     Dashboard
     ------------------------------------------------------- */

  {
    type: "single",

    key: "dashboard",

    label: "Dashboard",

    icon: "▦",
  },


  /* -------------------------------------------------------
     환자 관리
     ------------------------------------------------------- */

  {
    type: "single",

    key: "patients",

    label: "환자 관리",

    icon: "○",
  },


  /* -------------------------------------------------------
     진료 업무
     ------------------------------------------------------- */

  {
    type: "group",

    key: "clinical",

    label: "진료 업무",

    icon: "✓",

    children: [
      {
        key: "worklist",

        label: "Worklist",
      },

      {
        key: "triage",

        label: "접수 / Triage",
      },
    ],
  },


  /* -------------------------------------------------------
     검사 · 분석
     ------------------------------------------------------- */

  {
    type: "group",

    key: "analysis",

    label: "검사 · 분석",

    icon: "◇",

    children: [
      {
        key: "imaging",

        label: "검사 / 영상",
      },

      {
        key: "ai-results",

        label: "AI 분석 결과",
      },

      {
        key: "radiology-reports",

        label: "최종 판독",
      },

      {
        key: "cdss",

        label: "CDSS 결과",
      },
    ],
  },


  /* -------------------------------------------------------
     협진
     ------------------------------------------------------- */

  {
    type: "group",

    key: "consultation",

    label: "협진",

    icon: "◎",

    children: [
      {
        key: "consultations",

        label: "협진 목록",
      },

      {
        key: "surgical-planning",

        label: "수술 · 시술 플래닝",
      },
    ],
  },


  /* -------------------------------------------------------
     처방 / DUR
     ------------------------------------------------------- */

  {
    type: "single",

    key: "prescriptions",

    label: "처방 / DUR",

    icon: "+",
  },


  /* -------------------------------------------------------
     알림 센터
     ------------------------------------------------------- */

  {
    type: "single",

    key: "notifications",

    label: "알림 센터",

    icon: "!",
  },

];


/* =========================================================
   현재 메뉴가 어느 Group에 속하는지 확인
   ========================================================= */

function getMenuGroup(
  menu: SidebarMenuKey,
): SidebarGroupKey | null {

  if (
    menu === "worklist" ||
    menu === "triage"
  ) {
    return "clinical";
  }


  if (
    menu === "imaging" ||
    menu === "ai-results" ||
    menu === "radiology-reports" ||
    menu === "cdss"
  ) {
    return "analysis";
  }


  if (
    menu === "consultations" ||
    menu === "surgical-planning"
  ) {
    return "consultation";
  }


  return null;
}


/* =========================================================
   Sidebar
   ========================================================= */

export default function Sidebar({
  activeMenu,
  onMenuSelect,
}: SidebarProps) {


  /* ========================================================
     내부 Active Menu

     AppShell에서 activeMenu가 전달되면
     AppShell 상태를 우선 사용한다.
     ======================================================== */

  const [
    internalActiveMenu,
    setInternalActiveMenu,
  ] = useState<SidebarMenuKey>(
    "dashboard",
  );


  const currentActiveMenu =
    activeMenu ??
    internalActiveMenu;


  /* ========================================================
     현재 열려 있는 1Depth Group

     한 번에 하나의 Group만 펼친다.
     ======================================================== */

  const [
    openGroup,
    setOpenGroup,
  ] = useState<SidebarGroupKey | null>(
    null,
  );


  /* ========================================================
     현재 Active Menu가 2Depth 메뉴라면
     해당 부모 Group 자동 펼침
     ======================================================== */

  useEffect(() => {

    const parentGroup =
      getMenuGroup(
        currentActiveMenu,
      );


    if (parentGroup) {

      setOpenGroup(
        parentGroup,
      );

    }

  }, [
    currentActiveMenu,
  ]);


  /* ========================================================
     단일 / 2Depth 메뉴 선택
     ======================================================== */

  function handleMenuSelect(
    menu: SidebarMenuKey,
  ) {

    setInternalActiveMenu(
      menu,
    );


    onMenuSelect?.(
      menu,
    );

  }


  /* ========================================================
     1Depth Group 펼치기 / 닫기
     ======================================================== */

  function handleGroupToggle(
    group: SidebarGroupKey,
  ) {

    setOpenGroup(
      (previousGroup) =>
        previousGroup === group
          ? null
          : group,
    );

  }


  /* ========================================================
     Render
     ======================================================== */

  return (
    <aside className="sidebar">

      <nav
        className="sidebar-nav"
        aria-label="주요 메뉴"
      >

        <span className="sidebar-section-label">
          CLINICAL WORKSPACE
        </span>


        {menuItems.map((item) => {


          /* =================================================
             단일 1Depth 메뉴
             ================================================= */

          if (item.type === "single") {

            const isActive =
              currentActiveMenu ===
              item.key;


            return (
              <button
                key={item.key}
                type="button"
                className={
                  isActive
                    ? "sidebar-menu active"
                    : "sidebar-menu"
                }
                onClick={() => {
                  handleMenuSelect(
                    item.key,
                  );
                }}
              >

                <span
                  className="sidebar-menu-icon"
                  aria-hidden="true"
                >
                  {item.icon}
                </span>


                <span className="sidebar-menu-label">
                  {item.label}
                </span>

              </button>
            );

          }


          /* =================================================
             Group Menu
             ================================================= */

          const isOpen =
            openGroup ===
            item.key;


          const hasActiveChild =
            item.children.some(
              (child) =>
                child.key ===
                currentActiveMenu,
            );


          return (
            <div
              key={item.key}
              className={
                hasActiveChild
                  ? "sidebar-group active"
                  : "sidebar-group"
              }
            >

              {/* =============================================
                  1Depth
                  ============================================= */}

              <button
                type="button"
                className={
                  hasActiveChild
                    ? "sidebar-menu sidebar-group-button active"
                    : "sidebar-menu sidebar-group-button"
                }
                aria-expanded={
                  isOpen
                }
                onClick={() => {
                  handleGroupToggle(
                    item.key,
                  );
                }}
              >

                <span
                  className="sidebar-menu-icon"
                  aria-hidden="true"
                >
                  {item.icon}
                </span>


                <span className="sidebar-menu-label">
                  {item.label}
                </span>


                <span
                  className={
                    isOpen
                      ? "sidebar-group-arrow open"
                      : "sidebar-group-arrow"
                  }
                  aria-hidden="true"
                >
                  ▾
                </span>

              </button>


              {/* =============================================
                  2Depth
                  ============================================= */}

              {isOpen && (

                <div className="sidebar-submenu">

                  {item.children.map(
                    (child) => {

                      const isChildActive =
                        currentActiveMenu ===
                        child.key;


                      return (
                        <button
                          key={
                            child.key
                          }
                          type="button"
                          className={
                            isChildActive
                              ? "sidebar-submenu-item active"
                              : "sidebar-submenu-item"
                          }
                          onClick={() => {
                            handleMenuSelect(
                              child.key,
                            );
                          }}
                        >

                          <span
                            className="sidebar-submenu-dot"
                            aria-hidden="true"
                          >
                            ·
                          </span>


                          <span>
                            {
                              child.label
                            }
                          </span>

                        </button>
                      );

                    },
                  )}

                </div>

              )}

            </div>
          );

        })}

      </nav>


      <div className="sidebar-footer">

        <span>
          Brain CDSS
        </span>

        <small>
          Medical Workspace
        </small>

      </div>

    </aside>
  );
}