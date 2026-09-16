import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getAccessToken,
} from "../auth/session";

import "./admin.css";


const GRAFANA_LOGIN =
  "/grafana/login";

const GRAFANA_DASHBOARD =
  (
    "/grafana/d/"
    + "brainon-admin-overview/"
    + "brainon-admin-system-monitoring"
    + "?orgId=1&kiosk"
  );


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


  const connectGrafana =
    useCallback(
      async () => {
        const accessToken =
          getAccessToken();

        if (!accessToken) {
          setGrafanaReady(false);
          setLoading(false);

          setError(
            "BrainOn 로그인 정보가 없습니다.",
          );

          return;
        }


        setLoading(true);
        setError("");


        try {
          const response =
            await fetch(
              GRAFANA_LOGIN,
              {
                method: "GET",

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

        } catch (requestError) {

          setGrafanaReady(
            false,
          );

          setError(
            requestError
              instanceof Error
              ? requestError.message
              : (
                  "Grafana 연결에 "
                  + "실패했습니다."
                ),
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


  return (
    <section
      className="
        clinical-page
        admin-page
        admin-monitoring-page
      "
    >
      <header
        className="clinical-page__heading"
      >
        <div>
          <h2>
            시스템 모니터링
          </h2>

          <p>
            시스템 상태·DB·감사 로그·
            Runtime 로그·request_id를
            통합 추적합니다.
          </p>
        </div>

        <button
          type="button"
          className="
            admin-action
            admin-action--primary
          "
          disabled={loading}
          onClick={
            () =>
              void connectGrafana()
          }
        >
          {loading
            ? "연결 중..."
            : "모니터링 재연결"}
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
          <div className="clinical-card">
            <div className="clinical-state">
              Grafana 관리자 세션을
              연결하고 있습니다.
            </div>
          </div>
        )}


      {grafanaReady && (
        <section
          className="
            clinical-card
            admin-grafana-card
          "
        >
          <iframe
            title="BrainOn System Monitoring"
            className="admin-grafana-frame"
            src={GRAFANA_DASHBOARD}
          />
        </section>
      )}
    </section>
  );
}
