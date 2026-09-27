type ContextRecord = Record<string, unknown>;

const emergencyStatusLabels: Record<string, string> = {
  NOTIFIED: "확인 대기",
  ACKNOWLEDGED: "확인 완료",
};

function asRecord(value: unknown): ContextRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as ContextRecord
    : null;
}

function asText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function asCount(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0
    ? value
    : null;
}

export function prepareClinicalContextForPrompt(
  clinicalContext: ContextRecord,
): ContextRecord {
  const worklist = asRecord(clinicalContext.get_emergency_worklist);
  if (worklist === null) {
    return clinicalContext;
  }

  const patients = new Map<string, ContextRecord>();
  const items = Array.isArray(worklist.items) ? worklist.items : [];

  for (const [index, item] of items.entries()) {
    const event = asRecord(item);
    if (event === null) {
      continue;
    }

    const patientId = asText(event.patient_id);
    const patientName = asText(event.patient_name);
    const patientNo = asText(event.patient_no);
    const occurredAt = asText(event.occurred_at);
    const statusCode = asText(event.status);
    const status = statusCode === null
      ? null
      : emergencyStatusLabels[statusCode];
    const patient: ContextRecord = {};

    if (patientName !== null) patient.patient_name = patientName;
    if (patientNo !== null) patient.patient_no = patientNo;
    if (occurredAt !== null) patient.occurred_at = occurredAt;
    if (status !== undefined) patient.status = status;

    if (Object.keys(patient).length === 0) {
      continue;
    }

    const patientKey = patientId ?? `event-${index}`;
    if (!patients.has(patientKey)) {
      patients.set(patientKey, patient);
    }
  }

  const patientCount = asCount(worklist.patient_count) ?? patients.size;

  return {
    ...clinicalContext,
    get_emergency_worklist: {
      scope: "현재 종료되지 않은 진료 건에 연결된 응급 환자",
      patient_count: patientCount,
      patients: [...patients.values()],
    },
  };
}
