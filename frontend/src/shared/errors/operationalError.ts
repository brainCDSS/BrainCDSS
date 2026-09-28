export const OPERATIONAL_ERROR_EVENT =
  "brainon:operational-error";


export type OperationalErrorKind =
  | "server"
  | "network";


export type OperationalErrorPayload = {
  kind: OperationalErrorKind;
  status: number | null;

  /*
   * 관리자 추적용 원본 UUID.
   * 사용자 화면에는 직접 노출하지 않는다.
   */
  requestId: string | null;

  /*
   * 사용자/관리자가 공유하는 사람이 읽기 쉬운 코드.
   * 예: ERR-07949247B3154ABC
   */
  trackingCode: string | null;
};


export function trackingCodeFromRequestId(
  requestId: string | null | undefined,
): string | null {

  if (!requestId) {
    return null;
  }


  const compact =
    requestId.replace(
      /[^0-9a-f]/gi,
      "",
    );


  /*
   * UUID가 아닌 임의 문자열로 가짜 오류 코드를
   * 만들지 않는다.
   */
  if (compact.length < 16) {
    return null;
  }


  return (
    "ERR-"
    + compact
        .slice(0, 16)
        .toUpperCase()
  );
}


export function notifyOperationalError(
  payload: OperationalErrorPayload,
) {

  if (
    typeof window === "undefined"
  ) {
    return;
  }


  window.dispatchEvent(
    new CustomEvent<
      OperationalErrorPayload
    >(
      OPERATIONAL_ERROR_EVENT,
      {
        detail: payload,
      },
    ),
  );
}
