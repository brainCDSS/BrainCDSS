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

const GRAFANA_ACTIVE_VIEW_STORAGE_KEY =
  "brainon-grafana-active-view";


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
    id: "query-console",
    label: "Query Console",
    kind: "tool",
    path: "/explore",
  },

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
      "query-console",
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
   Audit · Request Trace
   Embedded Explore datasource URL
   ============================================================ */

type AuditExploreSource =
  | "explore-sql"
  | "explore-metrics"
  | "explore-logs";


function buildAuditExploreUrl(
  source: AuditExploreSource,
) {

  const config = {

    "explore-sql": {
      uid: "brainon-postgres",
      type: "postgres",

      query: {
        format: "table",
        rawSql: "",
        editorMode: "code",
      },
    },

    "explore-metrics": {
      uid: "prometheus",
      type: "prometheus",

      query: {
        expr: "",
        range: true,
        instant: false,
        editorMode: "code",
      },
    },

    "explore-logs": {
      uid: "loki",
      type: "loki",

      query: {
        expr: "",
        queryType: "range",
        editorMode: "code",
      },
    },

  }[source];


  const panes = {
    brainon: {

      /*
       * 중요:
       * pane datasource와
       * query datasource를 동일하게 지정한다.
       */
      datasource:
        config.uid,

      queries: [
        {
          refId: "A",

          datasource: {
            uid:
              config.uid,

            type:
              config.type,
          },

          ...config.query,
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
   * full kiosk
   *
   * Grafana 자체 상단 navigation /
   * sidebar를 숨긴다.
   */
  params.set(
    "kiosk",
    "1",
  );


  return (
    "/grafana/explore?"
    + params.toString()
  );
}


/*
 * Explore iframe은 같은 origin의 /grafana를 사용하므로
 * iframe 내부 breadcrumb만 추가로 숨길 수 있다.
 *
 * Grafana 버전에 따라 breadcrumb markup이 일부 달라질 수
 * 있으므로 semantic/test-id 기반 selector만 사용한다.
 */
function cleanAuditExploreFrame(
  frame: HTMLIFrameElement,
) {

  try {

    const doc =
      frame.contentDocument;


    if (!doc) {
      return;
    }


    const styleId =
      "brainon-audit-explore-clean";


    if (
      doc.getElementById(
        styleId,
      )
    ) {
      return;
    }


    const style =
      doc.createElement(
        "style",
      );


    style.id =
      styleId;


    style.textContent = `
      [data-testid*="Breadcrumb"],
      [aria-label*="Breadcrumb"] {
        display: none !important;
      }

      nav:has(
        [data-testid*="Breadcrumb"]
      ) {
        display: none !important;
      }

      nav:has(
        [aria-label*="Breadcrumb"]
      ) {
        display: none !important;
      }
    `;


    doc.head.appendChild(
      style,
    );

  } catch {
    /*
     * same-origin proxy 상태에서는 접근 가능.
     * 혹시 iframe origin 정책이 달라지더라도
     * Query Console 자체 동작은 유지한다.
     */
  }
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
    () => {
      try {
        const stored =
          sessionStorage.getItem(
            GRAFANA_ACTIVE_VIEW_STORAGE_KEY,
          );

        if (
          stored
          && GRAFANA_VIEWS.some(
            (item) =>
              item.id === stored,
          )
        ) {
          return stored;
        }
      } catch {
        // sessionStorage unavailable:
        // use default dashboard.
      }

      return "overview";
    },
  );


  useEffect(
    () => {
      try {
        sessionStorage.setItem(
          GRAFANA_ACTIVE_VIEW_STORAGE_KEY,
          activeViewId,
        );
      } catch {
        // Ignore storage restrictions.
      }
    },
    [
      activeViewId,
    ],
  );


  const [
    quickTraceInput,
    setQuickTraceInput,
  ] = useState("");


  const [
    appliedTrackingCode,
    setAppliedTrackingCode,
  ] = useState("");


  const [
    dashboardRange,
    setDashboardRange,
  ] = useState("24h");


  const [
    dashboardRefreshKey,
    setDashboardRefreshKey,
  ] = useState(0);


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


  const activeGrafanaUrl =
    useMemo(
      () => {

        const url =
          grafanaViewUrl(
            activeView,
          );


        if (
          activeView.kind
          !== "dashboard"
        ) {
          return url;
        }


        const params =
          new URLSearchParams();

        params.set(
          "_dash.hideTimePicker",
          "true",
        );

        params.set(
          "_dash.hideVariables",
          "true",
        );

        params.set(
          "_dash.hideLinks",
          "true",
        );

        params.set(
          "from",
          `now-${dashboardRange}`,
        );

        params.set(
          "to",
          "now",
        );


        if (
          activeView.id === "audit"
          && appliedTrackingCode
        ) {
          params.set(
            "var-tracking_code",
            appliedTrackingCode,
          );
        }


        return (
          url
          + (
            url.includes("?")
              ? "&"
              : "?"
          )
          + params.toString()
        );

      },
      [
        activeView,
        dashboardRange,
        appliedTrackingCode,
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


  function handleQuickDashboard(
    viewId: string,
  ) {

    const group =
      GRAFANA_GROUPS.find(
        (item) =>
          item.children.includes(
            viewId,
          )
          || item.directViewId
          === viewId,
      );


    setActiveViewId(
      viewId,
    );


    setExpandedGroup(
      group?.id
      ?? "overview",
    );
  }


  function handleQuickTraceSubmit(
    event:
      React.FormEvent<HTMLFormElement>,
  ) {

    event.preventDefault();


    const normalized =
      quickTraceInput
        .trim()
        .toUpperCase();


    if (
      normalized
      && !/^ERR-[0-9A-F]{16}$/.test(
        normalized,
      )
    ) {
      return;
    }


    setQuickTraceInput(
      normalized,
    );

    setAppliedTrackingCode(
      normalized,
    );

    setActiveViewId(
      "audit",
    );

    setExpandedGroup(
      "operations",
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


            {
              activeView.kind
              === "dashboard"
              && (
                <div
                  className="
                    brainon-ops-toolbar
                  "
                >
                  <form
                    className="
                      brainon-ops-trace-search
                    "
                    onSubmit={
                      handleQuickTraceSubmit
                    }
                  >
                    <span>
                      Error 추적번호
                    </span>

                    <input
                      value={
                        quickTraceInput
                      }
                      onChange={
                        (event) =>
                          setQuickTraceInput(
                            event.target.value,
                          )
                      }
                      placeholder="
                        ERR-0000000000000000
                      "
                      pattern="ERR-[0-9A-Fa-f]{16}"
                      title="ERR- 뒤에 16자리 Error 추적번호를 입력하세요."
                    />

                    <button
                      type="submit"
                    >
                      추적
                    </button>
                  </form>


                  <nav
                    className="
                      brainon-ops-quick-nav
                    "
                    aria-label="
                      운영 대시보드 바로가기
                    "
                  >
                    {
                      GRAFANA_VIEWS
                        .filter(
                          (view) =>
                            view.kind
                            === "dashboard",
                        )
                        .map(
                          (view) => (
                            <button
                              key={
                                view.id
                              }
                              type="button"
                              className={
                                (
                                  "brainon-ops-quick-nav__item "
                                  + (
                                    activeView.id
                                    === view.id
                                      ? "is-active"
                                      : ""
                                  )
                                )
                              }
                              onClick={
                                () =>
                                  handleQuickDashboard(
                                    view.id,
                                  )
                              }
                            >
                              {
                                view.label
                              }
                            </button>
                          ),
                        )
                    }
                  </nav>


                  <div
                    className="
                      brainon-ops-toolbar__controls
                    "
                  >
                    <select
                      value={
                        dashboardRange
                      }
                      onChange={
                        (event) =>
                          setDashboardRange(
                            event.target.value,
                          )
                      }
                      aria-label="
                        조회 기간
                      "
                    >
                      <option value="1h">
                        최근 1시간
                      </option>

                      <option value="6h">
                        최근 6시간
                      </option>

                      <option value="24h">
                        최근 24시간
                      </option>

                      <option value="7d">
                        최근 7일
                      </option>
                    </select>

                    <button
                      type="button"
                      onClick={
                        () =>
                          setDashboardRefreshKey(
                            (value) =>
                              value + 1,
                          )
                      }
                    >
                      ↻ 새로고침
                    </button>
                  </div>
                </div>
              )
            }


            {/* BRAINON_EXPLORE_QUERY_CONSOLE */}
            {activeViewId === "query-console" ? (
              <section
                className="
                  brainon-audit-query-console
                  brainon-explore-query-console
                "
              >
                <header
                  className="
                    brainon-audit-query-console__header
                  "
                >
                  <div
                    className="
                      brainon-audit-query-console__heading
                    "
                  >
                    <strong>
                      Query Console
                    </strong>

                    <span>
                      PostgreSQL · Prometheus · Loki
                      원본 데이터를 직접 조회합니다.
                    </span>
                  </div>

                  <label
                    className="
                      brainon-audit-query-console__source
                    "
                  >
                    <span>
                      Datasource
                    </span>

                    <select
                      defaultValue="explore-sql"
                      onChange={
                        (event) => {

                          const source =
                            event.target.value;


                          if (
                            source !== "explore-sql"
                            && source !== "explore-metrics"
                            && source !== "explore-logs"
                          ) {
                            return;
                          }


                          const consoleRoot =
                            event.currentTarget.closest(
                              ".brainon-explore-query-console",
                            );


                          const queryFrame =
                            consoleRoot?.querySelector<
                              HTMLIFrameElement
                            >(
                              ".brainon-audit-query-frame",
                            );


                          if (queryFrame) {
                            queryFrame.src =
                              buildAuditExploreUrl(
                                source,
                              );
                          }
                        }
                      }
                    >
                      <option
                        value="explore-sql"
                      >
                        PostgreSQL · SQL
                      </option>

                      <option
                        value="explore-metrics"
                      >
                        Prometheus · PromQL
                      </option>

                      <option
                        value="explore-logs"
                      >
                        Loki · LogQL
                      </option>
                    </select>
                  </label>
                </header>

                <iframe
                  title="
                    BrainOn Query Console
                  "
                  className="
                    brainon-audit-query-frame
                  "
                  src={
                    buildAuditExploreUrl(
                      "explore-sql",
                    )
                  }
                  onLoad={
                    (event) =>
                      cleanAuditExploreFrame(
                        event.currentTarget,
                      )
                  }
                />
              </section>
            ) : (
<iframe
              key={
                [
                  activeView.id,
                  dashboardRange,
                  dashboardRefreshKey,
                  appliedTrackingCode,
                ].join(":")
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
                activeGrafanaUrl
              }
            />
            )}

            {/* BRAINON_AUDIT_INLINE_EXPLORE */}
            {activeViewId === "audit" && (
              <section
                className="
                  brainon-audit-query-console
                "
              >
                <header
                  className="
                    brainon-audit-query-console__header
                  "
                >
                  <div
                    className="
                      brainon-audit-query-console__heading
                    "
                  >
                    <strong>
                      Query Console
                    </strong>

                    <span>
                      추적 결과를 DB · Metrics · Logs
                      원본 데이터로 바로 확인합니다.
                    </span>
                  </div>


                  {/* BRAINON_QUERY_CONSOLE_SHORTCUT */}
                  <button
                    type="button"
                    className="
                      brainon-query-console-shortcut
                    "
                    title="
                      Explore Query Console 바로가기
                    "
                    aria-label="
                      Explore Query Console 바로가기
                    "
                    onClick={
                      () => {
                        setActiveViewId(
                          "query-console",
                        );

                        setExpandedGroup(
                          "grafana-explore",
                        );

                        setNavigationExpanded(
                          true,
                        );
                      }
                    }
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M14 5h5v5" />
                      <path d="M10 14 19 5" />
                      <path d="M19 13v6H5V5h6" />
                    </svg>
                  </button>

                  <label
                    className="
                      brainon-audit-query-console__source
                    "
                  >
                    <span>
                      Datasource
                    </span>

                    <select
                      defaultValue="explore-sql"
                      onChange={
                        (event) => {

                          const source =
                            event.target.value;


                          if (
                            source !== "explore-sql"
                            && source !== "explore-metrics"
                            && source !== "explore-logs"
                          ) {
                            return;
                          }


                          const queryFrame =
                            document.querySelector<
                              HTMLIFrameElement
                            >(
                              ".brainon-audit-query-frame",
                            );


                          if (
                            queryFrame
                          ) {

                            queryFrame.src =
                              buildAuditExploreUrl(
                                source,
                              );
                          }
                        }
                      }
                    >
                      <option
                        value="explore-sql"
                      >
                        PostgreSQL · SQL
                      </option>

                      <option
                        value="explore-metrics"
                      >
                        Prometheus · PromQL
                      </option>

                      <option
                        value="explore-logs"
                      >
                        Loki · LogQL
                      </option>
                    </select>
                  </label>
                </header>


                <iframe
                  title="
                    Audit Query Console
                  "
                  className="
                    brainon-audit-query-frame
                  "
                  src={
                    buildAuditExploreUrl(
                      "explore-sql",
                    )
                  }
                  onLoad={
                    (event) =>
                      cleanAuditExploreFrame(
                        event.currentTarget,
                      )
                  }
                />
              </section>
            )}

          </section>
        </section>
      )}
    </section>
  );
}
