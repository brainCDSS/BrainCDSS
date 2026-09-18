import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type {
  LoginUser,
} from "../auth/types";

import {
  getPatient,
} from "../patients/api";

import type {
  Patient,
} from "../patients/types";

import {
  acknowledgeEmergencyEvent,
  getEmergencyWorklist,
} from "./api";

import type {
  EmergencyRedFlag,
  EmergencyWorklistItem,
} from "./types";

import {
  NOTIFICATION_STATE_CHANGED_EVENT,
} from "../notifications/events";

import "./css/emergency_alert.css";


interface EmergencyAlertHostProps {
  currentUser: LoginUser;

  onOpenPatient: (
    patient: Patient,
    encounterId: string,
  ) => void;
}


const POLL_INTERVAL_MS = 5000;


function formatDateTime(
  value: string | null,
): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return date.toLocaleString(
    "ko-KR",
    {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    },
  );
}


function patientAge(
  item: EmergencyWorklistItem,
): string {
  const estimated =
    item.patient_summary.estimated_age ??
    item.patient_summary.age;

  if (
    estimated !== null &&
    estimated !== undefined
  ) {
    return `${estimated}세`;
  }

  return "-";
}


function sexLabel(
  value: string | null | undefined,
): string {
  if (value === "M") {
    return "남";
  }

  if (value === "F") {
    return "여";
  }

  return value || "-";
}


function redFlagValue(
  item: EmergencyRedFlag,
): string {
  const values: string[] = [];

  if (item.value_text) {
    values.push(
      item.value_text,
    );
  }

  if (
    item.value_numeric !== null &&
    item.value_numeric !== undefined
  ) {
    values.push(
      `${item.value_numeric}${
        item.unit
          ? ` ${item.unit}`
          : ""
      }`,
    );
  }

  if (item.note) {
    values.push(
      item.note,
    );
  }

  return values.join(" · ");
}


export default function EmergencyAlertHost({
  currentUser,
  onOpenPatient,
}: EmergencyAlertHostProps) {
  const isNeurologist =
    currentUser.role.code ===
    "NEUROLOGIST";

  const [
    alerts,
    setAlerts,
  ] = useState<
    EmergencyWorklistItem[]
  >([]);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    acknowledging,
    setAcknowledging,
  ] = useState(false);

  const [
    opening,
    setOpening,
  ] = useState(false);

  const refreshingRef =
    useRef(false);


  const refresh =
    useCallback(
      async () => {
        if (
          !isNeurologist ||
          refreshingRef.current
        ) {
          return;
        }

        refreshingRef.current =
          true;

        try {
          const response =
            await getEmergencyWorklist({
              ackStatus:
                "UNACKNOWLEDGED",
            });

          const next = (
            response.results ?? []
          )
            .filter(
              (item) =>
                item.triage_priority ===
                  "URGENT" ||
                item.triage_priority ===
                  "EMERGENCY",
            )
            .sort(
              (left, right) => {
                const rank = (
                  priority: string,
                ) =>
                  priority ===
                  "EMERGENCY"
                    ? 2
                    : 1;

                const priorityDiff =
                  rank(
                    right.triage_priority,
                  ) -
                  rank(
                    left.triage_priority,
                  );

                if (
                  priorityDiff !== 0
                ) {
                  return priorityDiff;
                }

                return (
                  new Date(
                    right.event
                      .notified_at ??
                    0,
                  ).getTime() -
                  new Date(
                    left.event
                      .notified_at ??
                    0,
                  ).getTime()
                );
              },
            );

          setAlerts(
            next,
          );

          setError(
            null,
          );
        } catch (requestError) {
          console.error(
            "EMERGENCY_ALERT_REFRESH_FAILED",
            requestError,
          );

          setError(
            "긴급·응급 알림을 불러오지 못했습니다.",
          );
        } finally {
          refreshingRef.current =
            false;
        }
      },
      [
        isNeurologist,
      ],
    );


  useEffect(
    () => {
      if (!isNeurologist) {
        setAlerts([]);
        return;
      }

      void refresh();

      const timer =
        window.setInterval(
          () => {
            void refresh();
          },
          POLL_INTERVAL_MS,
        );

      const handleFocus = () => {
        void refresh();
      };

      const handleVisibility =
        () => {
          if (
            document.visibilityState ===
            "visible"
          ) {
            void refresh();
          }
        };

      const handleNotification =
        () => {
          void refresh();
        };

      window.addEventListener(
        "focus",
        handleFocus,
      );

      document.addEventListener(
        "visibilitychange",
        handleVisibility,
      );

      window.addEventListener(
        NOTIFICATION_STATE_CHANGED_EVENT,
        handleNotification,
      );

      return () => {
        window.clearInterval(
          timer,
        );

        window.removeEventListener(
          "focus",
          handleFocus,
        );

        document.removeEventListener(
          "visibilitychange",
          handleVisibility,
        );

        window.removeEventListener(
          NOTIFICATION_STATE_CHANGED_EVENT,
          handleNotification,
        );
      };
    },
    [
      isNeurologist,
      refresh,
    ],
  );


  const current =
    useMemo(
      () =>
        alerts.length
          ? alerts[0]
          : null,
      [
        alerts,
      ],
    );


  async function acknowledge() {
    if (
      !current ||
      acknowledging
    ) {
      return;
    }

    setAcknowledging(
      true,
    );

    setError(
      null,
    );

    try {
      await acknowledgeEmergencyEvent(
        current.event.id,
      );

      await refresh();
    } catch (requestError) {
      console.error(
        "EMERGENCY_ALERT_ACK_FAILED",
        requestError,
      );

      setError(
        "응급 알림 확인 처리에 실패했습니다.",
      );
    } finally {
      setAcknowledging(
        false,
      );
    }
  }


  async function openPatient() {
    if (
      !current ||
      opening
    ) {
      return;
    }

    const patientId =
      current.patient_summary
        .patient_id ??
      current.patient_summary.id;

    if (!patientId) {
      setError(
        "환자 식별정보를 찾을 수 없습니다.",
      );

      return;
    }

    setOpening(
      true,
    );

    setError(
      null,
    );

    try {
      try {
        await acknowledgeEmergencyEvent(
          current.event.id,
        );
      } catch (ackError) {
        console.warn(
          "EMERGENCY_ALERT_AUTO_ACK_FAILED",
          ackError,
        );
      }

      const patient =
        await getPatient(
          patientId,
        );

      onOpenPatient(
        patient,
        current.encounter_id,
      );

      await refresh();
    } catch (requestError) {
      console.error(
        "EMERGENCY_ALERT_OPEN_PATIENT_FAILED",
        requestError,
      );

      setError(
        "환자 진료 화면을 열지 못했습니다.",
      );
    } finally {
      setOpening(
        false,
      );
    }
  }


  if (
    !isNeurologist ||
    !current
  ) {
    return null;
  }


  const emergency =
    current.triage_priority ===
    "EMERGENCY";

  const patient =
    current.patient_summary;

  return (
    <div
      className="emergency-alert-layer"
      role="presentation"
    >
      <section
        className={[
          "emergency-alert-modal",
          emergency
            ? "is-emergency"
            : "is-urgent",
        ].join(" ")}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="emergency-alert-title"
        aria-describedby="emergency-alert-summary"
      >
        <header className="emergency-alert-header">
          <div>
            <span className="emergency-alert-kicker">
              {emergency
                ? "EMERGENCY"
                : "URGENT"}
            </span>

            <h2 id="emergency-alert-title">
              {emergency
                ? "응급 환자 발생"
                : "긴급 환자 발생"}
            </h2>

            <p>
              담당 신경과 의료진의
              즉시 확인이 필요합니다.
            </p>
          </div>

          <strong className="emergency-alert-priority">
            {current.triage_priority}
          </strong>
        </header>

        <div className="emergency-alert-patient">
          <strong>
            {patient.name ?? "-"}
          </strong>

          <span>
            {patient.patient_no ?? "-"}
          </span>

          <span>
            {sexLabel(
              patient.sex,
            )}
          </span>

          <span>
            {patientAge(
              current,
            )}
          </span>

          {patient.birth_date && (
            <span>
              생년월일 {
                patient.birth_date
              }
            </span>
          )}
        </div>

        <div
          className="emergency-alert-summary"
          id="emergency-alert-summary"
        >
          <section>
            <h3>초기평가 요약</h3>

            <dl>
              <div>
                <dt>증상</dt>
                <dd>
                  {current.symptom_note ||
                    "-"}
                </dd>
              </div>

              <div>
                <dt>증상 발생</dt>
                <dd>
                  {formatDateTime(
                    current.onset_at,
                  )}
                </dd>
              </div>

              <div>
                <dt>
                  Last Known Well
                </dt>
                <dd>
                  {formatDateTime(
                    current.lkw_at,
                  )}
                </dd>
              </div>

              <div>
                <dt>평가점수</dt>
                <dd>
                  {current.total_score ??
                    "-"}
                </dd>
              </div>

              <div>
                <dt>평가 완료</dt>
                <dd>
                  {formatDateTime(
                    current.completed_at,
                  )}
                </dd>
              </div>

              <div>
                <dt>담당 신경과</dt>
                <dd>
                  {
                    current
                      .assigned_neurologist
                      ?.name ?? "-"
                  }
                </dd>
              </div>
            </dl>
          </section>

          <section>
            <h3>주요 이상 소견</h3>

            {current.red_flags.length ? (
              <ul className="emergency-alert-redflags">
                {current.red_flags.map(
                  (item) => (
                    <li key={item.item_code}>
                      <strong>
                        {item.item_code}
                      </strong>

                      {redFlagValue(item) && (
                        <span>
                          {redFlagValue(item)}
                        </span>
                      )}
                    </li>
                  ),
                )}
              </ul>
            ) : (
              <p className="emergency-alert-empty">
                기록된 Red Flag 항목이 없습니다.
              </p>
            )}

            <div className="emergency-alert-allergy">
              <strong>알레르기</strong>

              <span>
                {patient.allergy_info ||
                  "기록 없음"}
              </span>
            </div>
          </section>
        </div>

        {error && (
          <div
            className="emergency-alert-error"
            role="alert"
          >
            {error}
          </div>
        )}

        <footer className="emergency-alert-footer">
          <span>
            미확인 긴급·응급 알림
            {" "}
            {alerts.length}건
          </span>

          <div>
            <button
              type="button"
              className="emergency-alert-button is-secondary"
              disabled={
                acknowledging ||
                opening
              }
              onClick={() =>
                void acknowledge()
              }
            >
              {acknowledging
                ? "처리 중..."
                : "확인"}
            </button>

            <button
              type="button"
              className="emergency-alert-button is-primary"
              disabled={
                acknowledging ||
                opening
              }
              onClick={() =>
                void openPatient()
              }
            >
              {opening
                ? "불러오는 중..."
                : "환자 진료 화면으로 이동"}
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
