import { useState } from "react";

import "./layout.css";


/* =========================================================
   Sidebar Menu Key
   ---------------------------------------------------------
   AppShell에서 어떤 메뉴가 선택되었는지 관리할 때
   동일한 key를 사용한다.
   ========================================================= */

export type SidebarMenuKey =
  | "dashboard"
  | "worklist"
  | "patients"
  | "triage"
  | "imaging"
  | "ai-results"
  | "cdss"
  | "consultations"
  | "prescriptions"
  | "notifications";


/* =========================================================
   Sidebar Props
   ========================================================= */

interface SidebarProps {

  /**
   * 현재 선택된 메뉴
   *
   * AppShell에서 전달할 수 있다.
   *
   * 아직 AppShell 연결 전에는
   * 내부 상태를 사용한다.
   */
  activeMenu?: SidebarMenuKey;


  /**
   * 메뉴를 클릭했을 때
   * 부모(AppShell)에게 선택된 menu key를 전달한다.
   */
  onMenuSelect?: (
    menu: SidebarMenuKey,
  ) => void;
}


/* =========================================================
   Sidebar Menu
   ========================================================= */

const menuItems: {
  key: SidebarMenuKey;
  label: string;
  icon: string;
}[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    icon: "▦",
  },
  {
    key: "worklist",
    label: "Worklist",
    icon: "☷",
  },
  {
    key: "patients",
    label: "환자 관리",
    icon: "○",
  },
  {
    key: "triage",
    label: "접수 / Triage",
    icon: "✓",
  },
  {
    key: "imaging",
    label: "검사 / 영상",
    icon: "▣",
  },
  {
    key: "ai-results",
    label: "AI / 판독 결과",
    icon: "◇",
  },
  {
    key: "cdss",
    label: "CDSS 결과",
    icon: "◆",
  },
  {
    key: "consultations",
    label: "협진",
    icon: "◎",
  },
  {
    key: "prescriptions",
    label: "처방 / DUR",
    icon: "+",
  },
  {
    key: "notifications",
    label: "알림 센터",
    icon: "!",
  },
];


/* =========================================================
   Sidebar
   ========================================================= */

export default function Sidebar({
  activeMenu,
  onMenuSelect,
}: SidebarProps) {

  /* ========================================================
     부모 연결 전 사용할 내부 선택 상태

     현재 단계에서도 메뉴 클릭 시
     active 디자인이 정상적으로 바뀌도록 한다.
     ======================================================== */

  const [
    internalActiveMenu,
    setInternalActiveMenu,
  ] = useState<SidebarMenuKey>("dashboard");


  /**
   * AppShell에서 activeMenu를 전달하면
   * 부모 상태를 우선 사용한다.
   *
   * 아직 전달하지 않았다면
   * Sidebar 내부 상태를 사용한다.
   */
  const currentActiveMenu =
    activeMenu ?? internalActiveMenu;


  /* ========================================================
     메뉴 클릭
     ======================================================== */

  function handleMenuSelect(
    menu: SidebarMenuKey,
  ) {

    /**
     * 현재 단계에서 active 표시 변경
     */
    setInternalActiveMenu(menu);


    /**
     * AppShell이 연결되어 있다면
     * 부모에게 선택한 메뉴 전달
     */
    onMenuSelect?.(menu);
  }


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

          /**
           * 현재 선택된 메뉴인지 확인
           */
          const isActive =
            currentActiveMenu === item.key;


          return (
            <button
              key={item.key}
              type="button"

              className={
                isActive
                  ? "sidebar-menu active"
                  : "sidebar-menu"
              }

              /**
               * Sidebar 메뉴 선택
               */
              onClick={() => {
                handleMenuSelect(item.key);
              }}
            >

              <span
                className="sidebar-menu-icon"
                aria-hidden="true"
              >
                {item.icon}
              </span>

              <span>
                {item.label}
              </span>

            </button>
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