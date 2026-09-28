/*
 * BrainOn patient age normalization.
 *
 * Priority:
 * 1. estimated_age
 * 2. birth_date -> 만 나이 계산
 * 3. legacy age
 *
 * DB/API 값을 변경하지 않고 화면 표시 기준만 통일한다.
 */

function finiteAge(
  value: unknown,
): number | null {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value)
  ) {
    return null;
  }

  const normalized = Math.trunc(value);

  if (
    normalized < 0 ||
    normalized > 150
  ) {
    return null;
  }

  return normalized;
}


function ageFromBirthDate(
  value: unknown,
): number | null {
  if (
    typeof value !== "string" ||
    !value.trim()
  ) {
    return null;
  }

  /*
   * YYYY-MM-DD를 Date(string)로 바로 파싱하면
   * timezone에 따라 날짜가 달라질 수 있으므로
   * 달력 값 자체를 직접 비교한다.
   */
  const match =
    value
      .trim()
      .match(
        /^(\d{4})-(\d{2})-(\d{2})/,
      );

  if (!match) {
    return null;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);

  if (
    !Number.isInteger(year) ||
    !Number.isInteger(month) ||
    !Number.isInteger(day) ||
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > 31
  ) {
    return null;
  }

  /*
   * 실제 존재하는 날짜인지 UTC 기준으로 검증한다.
   */
  const validationDate =
    new Date(
      Date.UTC(
        year,
        month - 1,
        day,
      ),
    );

  if (
    validationDate.getUTCFullYear() !== year ||
    validationDate.getUTCMonth() !==
      month - 1 ||
    validationDate.getUTCDate() !== day
  ) {
    return null;
  }

  const today = new Date();

  let age =
    today.getFullYear() - year;

  const beforeBirthday =
    today.getMonth() + 1 < month ||
    (
      today.getMonth() + 1 === month &&
      today.getDate() < day
    );

  if (beforeBirthday) {
    age -= 1;
  }

  /*
   * 미래 생년월일이나 비정상 나이는 표시하지 않는다.
   */
  if (
    age < 0 ||
    age > 150
  ) {
    return null;
  }

  return age;
}


export function getPatientAge(
  source: unknown,
): number | null {
  if (
    typeof source !== "object" ||
    source === null
  ) {
    return null;
  }

  const patient =
    source as Record<string, unknown>;

  const estimatedAge =
    finiteAge(
      patient.estimated_age,
    );

  if (estimatedAge !== null) {
    return estimatedAge;
  }

  const birthDateAge =
    ageFromBirthDate(
      patient.birth_date,
    );

  if (birthDateAge !== null) {
    return birthDateAge;
  }

  /*
   * Emergency 등 일부 기존 응답의 legacy age 필드.
   * estimated_age / birth_date보다 낮은 우선순위다.
   */
  return finiteAge(
    patient.age,
  );
}


export function formatPatientAge(
  source: unknown,
  empty = "-",
): string {
  const age =
    getPatientAge(source);

  return age === null
    ? empty
    : `${age}세`;
}
