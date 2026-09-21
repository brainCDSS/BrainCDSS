export interface AssessmentItemLike {
  item_code: string;
  value_text?: string | null;
  value_numeric?: number | string | null;
  value?: boolean | number | string;
  unit?: string | null;
}

const HIDDEN_ASSESSMENT_ITEM_CODES = new Set([
  "GCS",
  "NIHSS_TOTAL",
]);

export function filterAssessmentItemsForDisplay<
  T extends { item_code: string }
>(
  items: readonly T[] | null | undefined,
): T[] {
  return (items ?? []).filter(
    (item) =>
      !HIDDEN_ASSESSMENT_ITEM_CODES.has(
        item.item_code,
      ),
  );
}

export interface InitialAssessmentLike {
  status: string;
  total_score: number | null;
  triage_priority: string | null;
  onset_at?: string | null;
  lkw_at?: string | null;
  symptom_note?: string | null;
  assigned_neurologist?: {
    id: string;
    name: string;
  } | null;
  created_at?: string | null;
  updated_at?: string | null;
  items: AssessmentItemLike[];
}

export interface ParsedInitialAssessment {
  bpSys: string | null;
  bpDia: string | null;
  heartRate: string | null;
  respRate: string | null;
  bodyTemp: string | null;
  spo2: string | null;
  heightCm: string | null;
  weightKg: string | null;
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
  item: AssessmentItemLike | undefined,
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
  assessment: InitialAssessmentLike,
): ParsedInitialAssessment {
  const items = new Map(
    filterAssessmentItemsForDisplay(
      assessment.items,
    ).map(
      (item) => [item.item_code, item],
    ),
  );

  return {
    bpSys:
      assessmentItemValue(items.get("BP_SYS")) ??
      assessmentItemValue(items.get("SBP")),
    bpDia:
      assessmentItemValue(items.get("BP_DIA")) ??
      assessmentItemValue(items.get("DBP")),
    heartRate:
      assessmentItemValue(items.get("HEART_RATE")),
    respRate:
      assessmentItemValue(items.get("RESP_RATE")),
    bodyTemp:
      assessmentItemValue(items.get("BODY_TEMP")) ??
      assessmentItemValue(items.get("TEMPERATURE")),
    spo2:
      assessmentItemValue(items.get("SPO2")),
    heightCm:
      assessmentItemValue(items.get("HEIGHT_CM")),
    weightKg:
      assessmentItemValue(items.get("WEIGHT_KG")),
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

interface AssessmentWithStatusAndTime {
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
}

function newestByTimestamp<T extends AssessmentWithStatusAndTime>(
  assessments: T[],
): T[] {
  return [...assessments].sort(
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
  );
}

export function latestCompletedAssessment<
  T extends AssessmentWithStatusAndTime
>(
  assessments: T[],
): T | null {
  return newestByTimestamp(
    assessments.filter(
      (assessment) =>
        assessment.status.toUpperCase() ===
        "COMPLETED",
    ),
  )[0] ?? null;
}

export function latestDraftAssessment<
  T extends AssessmentWithStatusAndTime
>(
  assessments: T[],
): T | null {
  return newestByTimestamp(
    assessments.filter(
      (assessment) =>
        assessment.status.toUpperCase() ===
        "DRAFT",
    ),
  )[0] ?? null;
}
