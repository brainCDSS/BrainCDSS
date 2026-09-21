import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getAccessToken,
} from "../auth/session";

import "./admin.css";


const GRAFANA_LOGIN =
  "/grafana/login";


type GrafanaView = {
  id: string;
  label: string;

  kind:
    | "dashboard"
    | "tool";

  uid?: string;
  slug?: string;

  /*
   * Grafana native route.
   *
   * Examples:
   * /playlists/
   * /dashboard/snapshots
   * /library-panels/
   * /alerting/list
   */
  path?: string;

  /*
   * Explore shortcut.
   *
   * datasource UID/type을 지정하면
   * Explore가 해당 datasource를
   * 바로 선택해서 열린다.
   */
  datasourceUid?: string;
  datasourceType?: string;
};


type GrafanaNavGroup = {
  id: string;
  label: string;

  icon:
    | "home"
    | "services"
    | "operations"
    | "dashboards"
    | "explore"
    | "alerting"
    | "connections"
    | "administration";

  children: string[];

  /*
   * child가 없는 단독 native tool.
   */
  directViewId?: string;
};


/* ============================================================
   BrainOn Dashboard + Grafana Native Tools
   ============================================================ */

const GRAFANA_VIEWS: GrafanaView[] = [

  // ----------------------------------------------------------
  // BrainOn dashboards
  // ----------------------------------------------------------

  {
    id: "overview",
    label: "운영 Overview",
    kind: "dashboard",
    uid: "brainon-admin-overview",
    slug: "brainon-operations-overview",
  },

  {
    id: "api",
    label: "API · Performance",
    kind: "dashboard",
    uid: "brainon-admin-api",
    slug: "brainon-api-performance",
  },

  {
    id: "ai",
    label: "AI Operations",
    kind: "dashboard",
    uid: "brainon-admin-ai",
    slug: "brainon-ai-operations",
  },

  {
    id: "infrastructure",
    label: "Infrastructure",
    kind: "dashboard",
    uid: "brainon-admin-infrastructure",
    slug: "brainon-infrastructure",
  },

  {
    id: "async",
    label: "Async Processing",
    kind: "dashboard",
    uid: "brainon-admin-async",
    slug: "brainon-async-processing",
  },

  {
    id: "incidents",
    label: "Incidents",
    kind: "dashboard",
    uid: "brainon-admin-incidents",
    slug: "brainon-incidents",
  },

  {
    id: "audit",
    label: "Audit · Request Trace",
    kind: "dashboard",
    uid: "brainon-admin-audit-trace",
    slug: "brainon-audit-request-trace",
  },


  // ----------------------------------------------------------
  // Grafana Dashboards native tools
  // ----------------------------------------------------------

  {
    id: "playlists",
    label: "Playlists",
    kind: "tool",
    path: "/playlists/",
  },

  {
    id: "snapshots",
    label: "Snapshots",
    kind: "tool",
    path: "/dashboard/snapshots",
  },

  {
    id: "library-panels",
    label: "Library panels",
    kind: "tool",
    path: "/library-panels/",
  },

  {
    id: "public-dashboards",
    label: "Public dashboards",
    kind: "tool",
    path: "/public-dashboards/list",
  },


  // ----------------------------------------------------------
  // Grafana Explore
  // ----------------------------------------------------------

  /*
   * BrainOn PostgreSQL SQL Query Editor.
   */
  {
    id: "explore-sql",
    label: "SQL / PostgreSQL",
    kind: "tool",
    path: "/explore",
    datasourceUid: "brainon-postgres",
    datasourceType: "postgres",
  },

  /*
   * Prometheus Query Editor.
   */
  {
    id: "explore-metrics",
    label: "Metrics / Prometheus",
    kind: "tool",
    path: "/explore",
    datasourceUid: "prometheus",
    datasourceType: "prometheus",
  },

  /*
   * Loki Query Editor.
   */
  {
    id: "explore-logs",
    label: "Logs / Loki",
    kind: "tool",
    path: "/explore",
    datasourceUid: "loki",
    datasourceType: "loki",
  },


  // ----------------------------------------------------------
  // Grafana operational native tools
  // ----------------------------------------------------------

  {
    id: "alerting",
    label: "Alerting",
    kind: "tool",
    path: "/alerting/list",
  },

  {
    id: "connections",
    label: "Connections",
    kind: "tool",
    path: "/connections",
  },

  {
    id: "administration",
    label: "Administration",
    kind: "tool",
    path: "/admin",
  },
];


/* ============================================================
   Navigation Groups
   ============================================================ */

const GRAFANA_GROUPS: GrafanaNavGroup[] = [

  {
    id: "overview",
    label: "Overview",
    icon: "home",
    children: [
      "overview",
    ],
  },

  {
    id: "services",
    label: "Services",
    icon: "services",
    children: [
      "api",
      "ai",
      "infrastructure",
      "async",
    ],
  },

  {
    id: "operations",
    label: "Operations",
    icon: "operations",
    children: [
      "incidents",
      "audit",
    ],
  },


  /*
   * 실제 Grafana Dashboards 기본 기능.
   */
  {
    id: "grafana-dashboards",
    label: "Dashboards",
    icon: "dashboards",
    children: [
      "playlists",
      "snapshots",
      "library-panels",
      "public-dashboards",
    ],
  },


  /*
   * 실제 Grafana Explore 기능.
   *
   * SQL / Metrics / Logs를
   * BrainOn datasource로 바로 진입.
   */
  {
    id: "grafana-explore",
    label: "Explore",
    icon: "explore",
    children: [
      "explore-sql",
      "explore-metrics",
      "explore-logs",
    ],
  },


  /*
   * 아래 3개는 Grafana native 기능으로
   * 바로 이동.
   */
  {
    id: "grafana-alerting",
    label: "Alerting",
    icon: "alerting",
    children: [],
    directViewId: "alerting",
  },

  {
    id: "grafana-connections",
    label: "Connections",
    icon: "connections",
    children: [],
    directViewId: "connections",
  },

  {
    id: "grafana-administration",
    label: "Administration",
    icon: "administration",
    children: [],
    directViewId: "administration",
  },
];


/* ============================================================
   Grafana URL
   ============================================================ */

function buildExploreUrl(
  view: GrafanaView,
) {
  if (
    !view.datasourceUid
    || !view.datasourceType
  ) {
    return (
      "/grafana/explore"
      + "?orgId=1"
      + "&theme=dark"
      + "&kiosk"
    );
  }


  /*
   * Grafana Explore 공식 panes URL 구조.
   *
   * query 자체는 비워 둔다.
   *
   * 화면이 열리면:
   * PostgreSQL → SQL editor
   * Prometheus → PromQL
   * Loki       → LogQL
   *
   * 사용자가 직접 query를 작성한다.
   */
  const panes = {
    brainon: {
      datasource:
        view.datasourceUid,

      queries: [
        {
          refId: "A",

          datasource: {
            uid:
              view.datasourceUid,

            type:
              view.datasourceType,
          },
        },
      ],

      range: {
        from: "now-1h",
        to: "now",
      },
    },
  };


  const params =
    new URLSearchParams();

  params.set(
    "panes",
    JSON.stringify(
      panes,
    ),
  );

  params.set(
    "schemaVersion",
    "1",
  );

  params.set(
    "orgId",
    "1",
  );

  params.set(
    "theme",
    "dark",
  );

  /*
   * Grafana native left nav만 숨긴다.
   * Explore/Alerting/etc의 실제 내용과
   * query editor는 그대로 사용 가능.
   */
  params.append(
    "kiosk",
    "",
  );


  return (
    "/grafana/explore?"
    + params.toString()
  );
}


function grafanaViewUrl(
  view: GrafanaView,
) {

  if (
    view.kind === "dashboard"
  ) {
    if (
      !view.uid
      || !view.slug
    ) {
      throw new Error(
        "Grafana dashboard UID/slug missing.",
      );
    }


    return (
      "/grafana/d/"
      + view.uid
      + "/"
      + view.slug
      + "?orgId=1"
      + "&theme=dark"
      + "&kiosk"
    );
  }


  if (
    view.path === "/explore"
  ) {
    return buildExploreUrl(
      view,
    );
  }


  const separator =
    view.path?.includes("?")
      ? "&"
      : "?";


  return (
    "/grafana"
    + (
      view.path
      ?? "/"
    )
    + separator
    + "orgId=1"
    + "&theme=dark"
    + "&kiosk"
  );
}


/* ============================================================
   Navigation Icons
   ============================================================ */

function GrafanaNavIcon({
  name,
}: {
  name: GrafanaNavGroup["icon"];
}) {

  const commonProps = {
    viewBox:
      "0 0 24 24",

    fill:
      "none",

    stroke:
      "currentColor",

    strokeWidth:
      1.8,

    strokeLinecap:
      "round" as const,

    strokeLinejoin:
      "round" as const,

    "aria-hidden":
      true,
  };


  if (name === "home") {
    return (
      <svg {...commonProps}>
        <path d="m3 11 9-8 9 8" />
        <path d="M5 10v10h14V10" />
        <path d="M9 20v-6h6v6" />
      </svg>
    );
  }


  if (name === "services") {
    return (
      <svg {...commonProps}>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    );
  }


  if (name === "operations") {
    return (
      <svg {...commonProps}>
        <path d="M12 3 2.8 19h18.4L12 3Z" />
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
      </svg>
    );
  }


  if (name === "dashboards") {
    return (
      <svg {...commonProps}>
        <rect x="3" y="3" width="8" height="8" rx="1" />
        <rect x="13" y="3" width="8" height="5" rx="1" />
        <rect x="13" y="10" width="8" height="11" rx="1" />
        <rect x="3" y="13" width="8" height="8" rx="1" />
      </svg>
    );
  }


  if (name === "explore") {
    return (
      <svg {...commonProps}>
        <circle cx="12" cy="12" r="9" />
        <path d="m15 9-2 6-6 2 2-6 6-2Z" />
      </svg>
    );
  }


  if (name === "alerting") {
    return (
      <svg {...commonProps}>
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
        <path d="M10 21h4" />
      </svg>
    );
  }


  if (name === "connections") {
    return (
      <svg {...commonProps}>
        <circle cx="8" cy="12" r="3" />
        <circle cx="16" cy="12" r="3" />
        <path d="M11 12h2" />
        <path d="M5 12H3" />
        <path d="M21 12h-2" />
      </svg>
    );
  }


  return (
    <svg {...commonProps}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06A1.7 1.7 0 0 0 15.74 19.4a1.7 1.7 0 0 0-1.04 1.56V21h-3v-.04a1.7 1.7 0 0 0-1.04-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 15.74a1.7 1.7 0 0 0-1.56-1.04H5v-3h.44A1.7 1.7 0 0 0 7 10.66a1.7 1.7 0 0 0-.34-1.88l-.06-.06L8.72 6.6l.06.06A1.7 1.7 0 0 0 10.66 7a1.7 1.7 0 0 0 1.04-1.56V5h3v.44A1.7 1.7 0 0 0 15.74 7a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06A1.7 1.7 0 0 0 19.4 10.66a1.7 1.7 0 0 0 1.56 1.04H21v3h-.04A1.7 1.7 0 0 0 19.4 15Z" />
    </svg>
  );
}


function ChevronIcon({
  open,
}: {
  open: boolean;
}) {
  return (
    <svg
      className={
        (
          "brainon-ops-chevron "
          + (
            open
              ? "is-open"
              : ""
          )
        )
      }
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}


function HamburgerIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </svg>
  );
}


/* ============================================================
   Page
   ============================================================ */

export default function SystemMonitoringPage() {

  const [
    grafanaReady,
    setGrafanaReady,
  ] = useState(false);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    error,
    setError,
  ] = useState("");


  const [
    navigationExpanded,
    setNavigationExpanded,
  ] = useState(false);


  const [
    expandedGroup,
    setExpandedGroup,
  ] = useState<string | null>(
    "overview",
  );


  const [
    activeViewId,
    setActiveViewId,
  ] = useState(
    "overview",
  );


  const activeView =
    useMemo(
      () =>
        GRAFANA_VIEWS.find(
          (item) =>
            item.id
            === activeViewId,
        )
        ?? GRAFANA_VIEWS[0],
      [
        activeViewId,
      ],
    );


  const activeGroupId =
    useMemo(
      () => {

        const group =
          GRAFANA_GROUPS.find(
            (item) =>
              item.children.includes(
                activeViewId,
              )
              || item.directViewId
              === activeViewId,
          );


        return (
          group?.id
          ?? "overview"
        );

      },
      [
        activeViewId,
      ],
    );


  const connectGrafana =
    useCallback(
      async () => {

        const accessToken =
          getAccessToken();


        if (!accessToken) {

          setGrafanaReady(
            false,
          );

          setLoading(
            false,
          );

          setError(
            "BrainOn 로그인 정보가 없습니다.",
          );

          return;
        }


        setLoading(
          true,
        );

        setError(
          "",
        );


        try {

          const response =
            await fetch(
              GRAFANA_LOGIN,
              {
                method:
                  "GET",

                headers: {
                  Authorization:
                    `Bearer ${accessToken}`,
                },

                credentials:
                  "same-origin",

                cache:
                  "no-store",
              },
            );


          if (!response.ok) {

            throw new Error(
              (
                "GRAFANA_SSO_FAILED:"
                + response.status
              ),
            );
          }


          setGrafanaReady(
            true,
          );

        } catch (
          requestError
        ) {

          setGrafanaReady(
            false,
          );


          setError(
            requestError
              instanceof Error
              ? requestError.message
              : "Grafana 연결에 실패했습니다.",
          );

        } finally {

          setLoading(
            false,
          );
        }
      },
      [],
    );


  useEffect(
    () => {
      void connectGrafana();
    },
    [
      connectGrafana,
    ],
  );


  function handleHamburgerClick() {

    setNavigationExpanded(
      (current) => {

        const next =
          !current;


        if (next) {

          setExpandedGroup(
            activeGroupId,
          );
        }


        return next;
      },
    );
  }


  function handleViewSelect(
    groupId: string,
    viewId: string,
  ) {

    setActiveViewId(
      viewId,
    );


    setExpandedGroup(
      groupId,
    );
  }


  function handleGroupClick(
    group: GrafanaNavGroup,
  ) {

    /*
     * 단독 Grafana tool.
     *
     * Alerting /
     * Connections /
     * Administration
     */
    if (
      group.directViewId
    ) {

      setActiveViewId(
        group.directViewId,
      );


      if (!navigationExpanded) {

        setNavigationExpanded(
          true,
        );
      }


      return;
    }


    /*
     * 접힌 rail에서 section icon을 누르면:
     * panel을 펼치고 해당 group open.
     */
    if (!navigationExpanded) {

      setNavigationExpanded(
        true,
      );

      setExpandedGroup(
        group.id,
      );

      return;
    }


    /*
     * Grafana-style accordion.
     */
    setExpandedGroup(
      (current) =>
        current === group.id
          ? null
          : group.id,
    );
  }


  function handleHome() {

    setActiveViewId(
      "overview",
    );

    setExpandedGroup(
      "overview",
    );
  }


  return (
    <section
      className="
        clinical-page
        admin-page
        admin-monitoring-page
      "
    >
      <header
        className="
          clinical-page__heading
        "
      >
        <div>
          <h2>
            시스템 모니터링
          </h2>

          <p>
            BrainOn 운영 상태와 시스템 지표를
            통합 관리합니다.
          </p>
        </div>

        <button
          type="button"
          className="
            admin-action
            admin-action--primary
          "
          disabled={
            loading
          }
          onClick={
            () =>
              void connectGrafana()
          }
        >
          {
            loading
              ? "연결 중..."
              : "모니터링 재연결"
          }
        </button>
      </header>


      {error && (
        <div
          className="
            admin-message
            admin-message--error
          "
        >
          {error}
        </div>
      )}


      {!error
        && loading
        && (
          <div
            className="
              clinical-card
            "
          >
            <div
              className="
                clinical-state
              "
            >
              Grafana 관리자 세션을
              연결하고 있습니다.
            </div>
          </div>
        )}


      {grafanaReady && (
        <section
          className={
            (
              "brainon-grafana-shell "
              + (
                navigationExpanded
                  ? "is-navigation-expanded"
                  : ""
              )
            )
          }
        >
          <aside
            className="
              brainon-ops-navigation
            "
          >

            {/* Brand */}
            <button
              type="button"
              className="
                brainon-ops-brand
              "
              title="
                BrainOn Operations Home
              "
              onClick={
                handleHome
              }
            >
              <span
                className="
                  brainon-ops-icon-slot
                "
              >
                <img
                  src="/grafana/public/img/grafana_icon.svg"
                  alt=""
                />
              </span>

              <span
                className="
                  brainon-ops-brand-label
                "
              >
                BrainOn Ops
              </span>
            </button>


            {/* Hamburger */}
            <button
              type="button"
              className="
                brainon-ops-menu-toggle
              "
              aria-expanded={
                navigationExpanded
              }
              title={
                navigationExpanded
                  ? "메뉴 접기"
                  : "메뉴 펼치기"
              }
              onClick={
                handleHamburgerClick
              }
            >
              <span
                className="
                  brainon-ops-icon-slot
                "
              >
                <HamburgerIcon />
              </span>

              <span
                className="
                  brainon-ops-menu-label
                "
              >
                Navigation
              </span>
            </button>


            <nav
              className="
                brainon-ops-groups
              "
              aria-label="
                BrainOn Grafana Navigation
              "
            >
              {GRAFANA_GROUPS.map(
                (group) => {

                  const isOpen =
                    expandedGroup
                    === group.id;

                  const containsActive =
                    activeGroupId
                    === group.id;

                  const hasChildren =
                    group.children.length
                    > 0;


                  return (
                    <section
                      key={
                        group.id
                      }
                      className={
                        (
                          "brainon-ops-group "
                          + (
                            isOpen
                              ? "is-open "
                              : ""
                          )
                          + (
                            containsActive
                              ? "contains-active"
                              : ""
                          )
                        )
                      }
                    >
                      <button
                        type="button"
                        className="
                          brainon-ops-group-button
                        "
                        aria-expanded={
                          hasChildren
                            ? isOpen
                            : undefined
                        }
                        title={
                          group.label
                        }
                        onClick={
                          () =>
                            handleGroupClick(
                              group,
                            )
                        }
                      >
                        <span
                          className="
                            brainon-ops-icon-slot
                          "
                        >
                          <GrafanaNavIcon
                            name={
                              group.icon
                            }
                          />
                        </span>

                        <span
                          className="
                            brainon-ops-group-label
                          "
                        >
                          {group.label}
                        </span>


                        {hasChildren && (
                          <ChevronIcon
                            open={
                              isOpen
                            }
                          />
                        )}
                      </button>


                      {hasChildren && (
                        <div
                          className="
                            brainon-ops-submenu
                          "
                        >
                          {group.children.map(
                            (
                              viewId,
                            ) => {

                              const view =
                                GRAFANA_VIEWS.find(
                                  (item) =>
                                    item.id
                                    === viewId,
                                );


                              if (!view) {
                                return null;
                              }


                              const active =
                                activeViewId
                                === view.id;


                              return (
                                <button
                                  key={
                                    view.id
                                  }
                                  type="button"
                                  className={
                                    (
                                      "brainon-ops-submenu-item "
                                      + (
                                        active
                                          ? "is-active"
                                          : ""
                                      )
                                    )
                                  }
                                  onClick={
                                    () =>
                                      handleViewSelect(
                                        group.id,
                                        view.id,
                                      )
                                  }
                                >
                                  <span
                                    className="
                                      brainon-ops-submenu-guide
                                    "
                                  />

                                  <span>
                                    {
                                      view.label
                                    }
                                  </span>
                                </button>
                              );
                            },
                          )}
                        </div>
                      )}
                    </section>
                  );
                },
              )}
            </nav>


            <footer
              className="
                brainon-ops-navigation-footer
              "
            >
              <span
                className="
                  brainon-ops-icon-slot
                "
              >
                ●
              </span>

              <span
                className="
                  brainon-ops-footer-label
                "
              >
                SYSTEM_ADMIN
              </span>
            </footer>
          </aside>


          <section
            className="
              brainon-grafana-content
            "
          >
            <div
              className="
                brainon-grafana-context-bar
              "
            >
              <div>
                <strong>
                  {
                    activeView.label
                  }
                </strong>

                <span>
                  {
                    activeView.kind
                    === "dashboard"
                      ? "BrainOn Operations Console"
                      : "Grafana Native Tool"
                  }
                </span>
              </div>
            </div>


            <iframe
              key={
                activeView.id
              }
              title={
                (
                  "BrainOn Grafana - "
                  + activeView.label
                )
              }
              className="
                brainon-grafana-frame
              "
              src={
                grafanaViewUrl(
                  activeView,
                )
              }
            />
          </section>
        </section>
      )}
    </section>
  );
}
