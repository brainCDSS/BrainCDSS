import { getPatientAge } from "../../lib/patientAge";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getApiRequestStatus } from "../../api/client";
import type { LoginUser } from "../auth/types";
import {
  emitNotificationStateChanged,
  NOTIFICATION_STATE_CHANGED_EVENT,
} from "../notifications/events";
import { getNotifications, markNotificationRead } from "../notifications/api";
import type { NotificationItem } from "../notifications/types";
import { getPatient } from "../patients/api";
import type { Patient } from "../patients/types";
import { acknowledgeEmergencyEvent, getEmergencyWorklist } from "./api";
import EmergencyPatientAlert, {
  type EmergencyAlertPriority,
  type EmergencyAlertTone,
  type EmergencyAlertValue,
} from "./EmergencyPatientAlert";
import type { EmergencyAssessmentItem, EmergencyWorklistItem } from "./types";

interface EmergencyAlertHostProps {
  currentUser: LoginUser;
  onOpenPatient: (patient: Patient, encounterId: string) => void;
  onOpenFallback: () => void;
}

interface RuntimeEmergencyAlert {
  notification: NotificationItem;
  worklistItem: EmergencyWorklistItem;
  priority: EmergencyAlertPriority;
  patientId: string;
  encounterId: string;
  emergencyEventId: string;
}

function stringData(notification: NotificationItem, key: string): string {
  const value = notification.data[key];
  return typeof value === "string" ? value.trim() : "";
}

function runtimePriority(notification: NotificationItem): EmergencyAlertPriority | null {
  const value = stringData(notification, "triage_priority").toUpperCase();
  return value === "EMERGENCY" || value === "URGENT" ? value : null;
}

export function buildRuntimeEmergencyQueue(
  notifications: NotificationItem[],
  worklist: EmergencyWorklistItem[],
): RuntimeEmergencyAlert[] {
  const worklistByEventId = new Map(
    worklist.map((item) => [item.event.id, item]),
  );
  const seenNotifications = new Set<string>();
  const seenEvents = new Set<string>();

  return notifications.flatMap((notification) => {
    const priority = runtimePriority(notification);
    const emergencyEventId = stringData(notification, "emergency_event_id");
    const patientId = stringData(notification, "patient_id");
    const encounterId = stringData(notification, "encounter_id");
    const item = worklistByEventId.get(emergencyEventId);

    if (
      notification.category !== "EMERGENCY" ||
      notification.is_read ||
      !priority ||
      !emergencyEventId ||
      !item ||
      seenNotifications.has(notification.id) ||
      seenEvents.has(emergencyEventId)
    ) {
      return [];
    }

    seenNotifications.add(notification.id);
    seenEvents.add(emergencyEventId);
    return [{
      notification,
      worklistItem: item,
      priority,
      patientId,
      encounterId,
      emergencyEventId,
    }];
  });
}

function formatDateTime(value: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function findItem(items: EmergencyAssessmentItem[], ...codes: string[]): EmergencyAssessmentItem | undefined {
  const wanted = new Set(codes.map((code) => code.toUpperCase()));
  return items.find((item) => wanted.has(item.item_code.toUpperCase()));
}

function itemTone(item: EmergencyAssessmentItem | undefined): EmergencyAlertTone {
  return item?.is_red_flag ? "danger" : "neutral";
}

function itemValue(item: EmergencyAssessmentItem | undefined): EmergencyAlertValue {
  return {
    value: item?.value_text?.trim() || (item?.value_numeric ?? (item?.note?.trim() || null)),
    tone: itemTone(item),
  };
}

function alreadyAcknowledged(error: unknown): boolean {
  return getApiRequestStatus(error) === 409;
}

export default function EmergencyAlertHost({
  currentUser,
  onOpenPatient,
  onOpenFallback,
}: EmergencyAlertHostProps) {
  const canReceiveClinicalAlerts = currentUser.role.code === "NEUROLOGIST";
  const [alerts, setAlerts] = useState<RuntimeEmergencyAlert[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [closed, setClosed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const refreshingRef = useRef(false);
  const alertIdsRef = useRef("");

  const refresh = useCallback(async () => {
    if (!canReceiveClinicalAlerts || refreshingRef.current) return;
    refreshingRef.current = true;
    try {
      const [notificationResponse, worklistResponse] = await Promise.all([
        getNotifications({ unreadOnly: true, category: "EMERGENCY" }),
        getEmergencyWorklist({ ackStatus: "UNACKNOWLEDGED" }),
      ]);
      const next = buildRuntimeEmergencyQueue(
        notificationResponse.results ?? [],
        worklistResponse.results ?? [],
      );
      const nextIds = next.map((alert) => alert.notification.id).join("|");
      if (nextIds !== alertIdsRef.current) {
        alertIdsRef.current = nextIds;
        setClosed(false);
      }
      setAlerts(next);
      setError(null);
    } catch (requestError) {
      console.error("EMERGENCY_ALERT_REFRESH_FAILED", requestError);
      setError("긴급·응급 알림을 불러오지 못했습니다.");
    } finally {
      refreshingRef.current = false;
    }
  }, [canReceiveClinicalAlerts]);

  useEffect(() => {
    if (!canReceiveClinicalAlerts) {
      setAlerts([]);
      return;
    }

    void refresh();
    const handleFocus = () => void refresh();
    const handleVisibility = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    const handleNotification = () => void refresh();

    window.addEventListener("focus", handleFocus);
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener(NOTIFICATION_STATE_CHANGED_EVENT, handleNotification);
    return () => {
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener(NOTIFICATION_STATE_CHANGED_EVENT, handleNotification);
    };
  }, [canReceiveClinicalAlerts, refresh]);

  useEffect(() => {
    if (alerts.length === 0) setCurrentIndex(0);
    else if (currentIndex >= alerts.length) setCurrentIndex(alerts.length - 1);
  }, [alerts.length, currentIndex]);

  const current = useMemo(() => alerts[currentIndex] ?? null, [alerts, currentIndex]);

  function removeCurrentAlert(alert: RuntimeEmergencyAlert) {
    setAlerts((items) => items.filter(
      (item) => item.notification.id !== alert.notification.id,
    ));
  }

  async function applyAcknowledgement(alert: RuntimeEmergencyAlert): Promise<void> {
    try {
      await acknowledgeEmergencyEvent(alert.emergencyEventId);
    } catch (requestError) {
      if (!alreadyAcknowledged(requestError)) throw requestError;
    }
    await markNotificationRead(alert.notification.id);
  }

  async function acknowledge() {
    if (!current || processing) return;
    setProcessing(true);
    setError(null);
    try {
      await applyAcknowledgement(current);
      removeCurrentAlert(current);
      emitNotificationStateChanged();
    } catch (requestError) {
      console.error("EMERGENCY_ALERT_ACK_FAILED", requestError);
      setError("응급 알림 확인 처리에 실패했습니다. 다시 시도해 주세요.");
    } finally {
      setProcessing(false);
    }
  }

  async function openPatient() {
    if (!current || processing) return;
    if (!current.patientId || !current.encounterId) {
      onOpenFallback();
      return;
    }

    setProcessing(true);
    setError(null);
    const [patientResult, acknowledgementResult] = await Promise.allSettled([
      getPatient(current.patientId),
      applyAcknowledgement(current),
    ]);

    if (acknowledgementResult.status === "rejected") {
      console.warn("EMERGENCY_ALERT_AUTO_ACK_FAILED", acknowledgementResult.reason);
    }

    if (patientResult.status === "fulfilled") {
      onOpenPatient(patientResult.value, current.encounterId);
      removeCurrentAlert(current);
      if (acknowledgementResult.status === "fulfilled") {
        emitNotificationStateChanged();
      }
    } else {
      console.error("EMERGENCY_ALERT_OPEN_PATIENT_FAILED", patientResult.reason);
      setError("환자 진료 화면을 열지 못해 알림 센터로 이동합니다.");
      onOpenFallback();
    }
    setProcessing(false);
  }

  if (!canReceiveClinicalAlerts || !current || closed) return null;

  const item = current.worklistItem;
  const assessmentItems = item.assessment_items ?? [];
  const patient = item.patient_summary;
  const age = getPatientAge(patient);

  return (
    <EmergencyPatientAlert
      priority={current.priority}
      eventId={current.emergencyEventId}
      patientId={current.patientId}
      patientNumber={patient.patient_no}
      patientName={patient.name}
      sex={patient.sex}
      age={age}
      encounterId={current.encounterId}
      visitAt={formatDateTime(item.arrived_at)}
      assessmentAt={formatDateTime(item.completed_at)}
      symptomOnsetAt={formatDateTime(item.onset_at)}
      lkwAt={formatDateTime(item.lkw_at)}
      assessorName={item.assessor?.name}
      consciousness={itemValue(findItem(assessmentItems, "CONSCIOUSNESS")).value}
      fast={{
        face: itemValue(findItem(assessmentItems, "FAST_FACE", "FACE")),
        arm: itemValue(findItem(assessmentItems, "FAST_ARM", "ARM")),
        speech: itemValue(findItem(assessmentItems, "FAST_SPEECH", "SPEECH")),
      }}
      vitals={{
        systolicBp: itemValue(findItem(assessmentItems, "BP_SYS", "SBP")),
        diastolicBp: itemValue(findItem(assessmentItems, "BP_DIA", "DBP")),
        heartRate: itemValue(findItem(assessmentItems, "HEART_RATE", "HR")),
        spo2: itemValue(findItem(assessmentItems, "SPO2")),
        bodyTemperature: itemValue(findItem(assessmentItems, "BODY_TEMP", "TEMPERATURE", "BT")),
      }}
      allergy={patient.allergy_info}
      mainSymptoms={item.symptom_note}
      specialNotes={null}
      currentIndex={currentIndex + 1}
      totalCount={alerts.length}
      acknowledged={false}
      busy={processing}
      errorMessage={error}
      onPrevious={() => setCurrentIndex((index) =>
        (index - 1 + alerts.length) % alerts.length)}
      onNext={() => setCurrentIndex((index) => (index + 1) % alerts.length)}
      onClose={() => setClosed(true)}
      onAcknowledge={() => void acknowledge()}
      onOpenPatient={() => void openPatient()}
    />
  );
}
