import type {
  AssessmentDetailResponse,
  AssessmentItem,
} from "./types";

export interface ParsedInitialAssessment {
  bpSys: string | null;
  bpDia: string | null;
  heartRate: string | null;
  respRate: string | null;
  bodyTemp: string | null;
  fastFace: string | null;
  fastArm: string | null;
  fastSpeech: string | null;
  balance: string | null;
  eyes: string | null;
  face: string | null;
  arm: string | null;
  speech: string | null;
  consciousness: string | null;
  totalScore: number | null;
  triagePriority: string | null;
  onsetAt: string | null;
  lkwAt: string | null;
  symptomNote: string | null;
  status: string;
}

export function assessmentItemValue(
  item: AssessmentItem | undefined,
): string | null {
  if (!item) {
    return null;
  }

  const value =
    item.value_numeric ??
    item.value_text ??
    item.value;

  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  return item.unit
    ? `${String(value)} ${item.unit}`
    : String(value);
}

export function parseInitialAssessment(
  assessment: AssessmentDetailResponse,
): ParsedInitialAssessment {
  const items = new Map(
    (assessment.items ?? []).map(
      (item) => [item.item_code, item],
    ),
  );

  return {
    bpSys: assessmentItemValue(items.get("BP_SYS")),
    bpDia: assessmentItemValue(items.get("BP_DIA")),
    heartRate: assessmentItemValue(items.get("HEART_RATE")),
    respRate: assessmentItemValue(items.get("RESP_RATE")),
    bodyTemp:
      assessmentItemValue(items.get("BODY_TEMP")) ??
      assessmentItemValue(items.get("TEMPERATURE")),
    fastFace: assessmentItemValue(items.get("FAST_FACE")),
    fastArm: assessmentItemValue(items.get("FAST_ARM")),
    fastSpeech: assessmentItemValue(items.get("FAST_SPEECH")),
    balance: assessmentItemValue(items.get("BALANCE")),
    eyes: assessmentItemValue(items.get("EYES")),
    face: assessmentItemValue(items.get("FACE")),
    arm: assessmentItemValue(items.get("ARM")),
    speech: assessmentItemValue(items.get("SPEECH")),
    consciousness: assessmentItemValue(items.get("CONSCIOUSNESS")),
    totalScore: assessment.total_score,
    triagePriority: assessment.triage_priority,
    onsetAt: assessment.onset_at ?? null,
    lkwAt: assessment.lkw_at ?? null,
    symptomNote: assessment.symptom_note ?? null,
    status: assessment.status,
  };
}

export function latestCompletedAssessment<
  T extends Pick<
    AssessmentDetailResponse,
    "status" | "created_at" | "updated_at"
  >
>(
  assessments: T[],
): T | null {
  return assessments
    .filter(
      (assessment) =>
        assessment.status.toUpperCase() ===
        "COMPLETED",
    )
    .sort(
      (left, right) =>
        (
          right.updated_at ??
          right.created_at ??
          ""
        ).localeCompare(
          left.updated_at ??
          left.created_at ??
          "",
        ),
    )[0] ?? null;
}

export function latestDraftAssessment<
  T extends Pick<
    AssessmentDetailResponse,
    "status" | "created_at" | "updated_at"
  >
>(
  assessments: T[],
): T | null {
  return assessments
    .filter(
      (assessment) =>
        assessment.status.toUpperCase() ===
        "DRAFT",
    )
    .sort(
      (left, right) =>
        (
          right.updated_at ??
          right.created_at ??
          ""
        ).localeCompare(
          left.updated_at ??
          left.created_at ??
          "",
        ),
    )[0] ?? null;
}
