/** Native date/datetime-local 값의 연도 부분을 네 자리로 제한한다. */
export function limitDateYear(value: string): string {
  if (!value) return "";
  const separatorIndex = value.indexOf("-");
  if (separatorIndex < 0) return value.slice(0, 4);
  const year = value.slice(0, separatorIndex).replace(/\D/g, "");
  return `${year.slice(0, 4)}${value.slice(separatorIndex)}`;
}

/** 휴대전화 입력을 숫자 11자리로 제한하고 010-XXXX-XXXX 형태로 표시한다. */
export function formatMobilePhone(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 3) return digits;
  if (digits.length <= 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
}
