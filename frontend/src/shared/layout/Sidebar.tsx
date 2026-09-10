import {
  useEffect,
  useState,
} from "react";

import "./layout.css";
import { MENU_LABELS } from "./menuConfig";


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
  | "appointments"

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
   접힘 Sidebar용 Lucide 스타일 아이콘
   ---------------------------------------------------------
   별도 아이콘 dependency 없이 이 파일 안에서 관리한다.
   아이콘을 바꾸려면 아래 이름과 SidebarIcon의 path만 수정한다.
   ========================================================= */

type SidebarIconName =
  | "home"
  | "users"
  | "stethoscope"
  | "scan-line"
  | "messages-square"
  | "pill"
  | "bell";


function SidebarIcon({
  name,
}: {
  name: SidebarIconName;
}) {

  const paths: Record<SidebarIconName, React.ReactNode> = {
    home: <><path d="m3 11 9-8 9 8" /><path d="M5 10v10h14V10" /><path d="M9 20v-6h6v6" /></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></>,
    stethoscope: <><path d="M11 2v2" /><path d="M5 2v2" /><path d="M5 3H4a2 2 0 0 0-2 2v3a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1" /><path d="M8 14a6 6 0 0 0 12 0v-3" /><circle cx="20" cy="10" r="2" /></>,
    "scan-line": <><path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" /><path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" /><path d="M7 12h10" /></>,
    "messages-square": <><path d="M7 18H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2v2" /><path d="m2 16 4 4v-4" /><path d="M10 11a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2l-4 3v-3h-2a2 2 0 0 1-2-2z" /></>,
    pill: <><path d="m10.5 20.5 10-10a4.95 4.95 0 0 0-7-7l-10 10a4.95 4.95 0 0 0 7 7Z" /><path d="m8.5 8.5 7 7" /></>,
    bell: <><path d="M10.27 21a2 2 0 0 0 3.46 0" /><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /></>,
  };


  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );

}


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

  icon: SidebarIconName;

  collapsedLabel: string;
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

  icon: SidebarIconName;

  collapsedLabel: string;

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

    label: MENU_LABELS.dashboard,

    icon: "home",

    collapsedLabel: "홈",
  },


  /* -------------------------------------------------------
     환자 관리
     ------------------------------------------------------- */

  {
    type: "single",

    key: "patients",

    label: MENU_LABELS.patients,

    icon: "users",

    collapsedLabel: "환자",
  },


  /* -------------------------------------------------------
     진료 업무
     ------------------------------------------------------- */

  {
    type: "group",

    key: "clinical",

    label: "진료 업무",

    icon: "stethoscope",

    collapsedLabel: "진료",

    children: [
      {
        key: "triage",

        label: MENU_LABELS.triage,
      },

      {
        key: "worklist",

        label: MENU_LABELS.worklist,
      },
      {
        key: "appointments",

        label: MENU_LABELS.appointments,
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

    icon: "scan-line",

    collapsedLabel: "검사",

    children: [
      {
        key: "imaging",

        label: MENU_LABELS.imaging,
      },

      {
        key: "ai-results",

        label: MENU_LABELS["ai-results"],
      },

      {
        key: "radiology-reports",

        label: MENU_LABELS["radiology-reports"],
      },

      {
        key: "cdss",

        label: MENU_LABELS.cdss,
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

    icon: "messages-square",

    collapsedLabel: "협진",

    children: [
      {
        key: "consultations",

        label: MENU_LABELS.consultations,
      },

      {
        key: "surgical-planning",

        label: MENU_LABELS["surgical-planning"],
      },
    ],
  },


  /* -------------------------------------------------------
     처방 / DUR
     ------------------------------------------------------- */

  {
    type: "single",

    key: "prescriptions",

    label: MENU_LABELS.prescriptions,

    icon: "pill",

    collapsedLabel: "처방",
  },


  /* -------------------------------------------------------
     알림 센터
     ------------------------------------------------------- */

  {
    type: "single",

    key: "notifications",

    label: MENU_LABELS.notifications,

    icon: "bell",

    collapsedLabel: "알림",
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
    menu === "triage" ||
    menu === "appointments"
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
                    ? "sidebar-menu sidebar-page-menu active"
                    : "sidebar-menu sidebar-page-menu"
                }
                onClick={() => {
                  handleMenuSelect(
                    item.key,
                  );
                }}
                title={item.label}
              >

                <span
                  className="sidebar-menu-icon"
                  aria-hidden="true"
                >
                  <SidebarIcon name={item.icon} />
                </span>


                <span className="sidebar-menu-label">
                  {item.label}
                </span>

                {/* 접힌 상태에서만 표시되는 짧은 메뉴명 */}
                <span className="sidebar-collapsed-label">
                  {item.collapsedLabel}
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


          return (
            <div
              key={item.key}
              className="sidebar-group"
            >

              {/* =============================================
                  1Depth
                  ============================================= */}

              <button
                type="button"
                className={
                  isOpen
                    ? "sidebar-menu sidebar-group-button expanded"
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
                title={item.label}
              >

                <span
                  className="sidebar-menu-icon"
                  aria-hidden="true"
                >
                  <SidebarIcon name={item.icon} />
                </span>


                <span className="sidebar-menu-label">
                  {item.label}
                </span>

                {/* 접힌 상태에서만 표시되는 짧은 그룹명 */}
                <span className="sidebar-collapsed-label">
                  {item.collapsedLabel}
                </span>


                <span
                  className={
                    isOpen
                      ? "sidebar-group-arrow open"
                      : "sidebar-group-arrow"
                  }
                  aria-hidden="true"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="m6 9 6 6 6-6" />
                  </svg>
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
                              ? "sidebar-submenu-item sidebar-page-menu active"
                              : "sidebar-submenu-item sidebar-page-menu"
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
                          />


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
