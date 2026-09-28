import {
  getAccessToken,
} from "../features/auth/session";

import {
  notifyOperationalError,
  trackingCodeFromRequestId,
} from "../shared/errors/operationalError";


/**
 * Single boundary for backend HTTP calls.
 * Never call internal services from the browser.
 */
const baseUrl =
  import.meta.env.DEV
    ? ""
    : import.meta.env.VITE_BACKEND_URL ?? "";


export class ApiRequestError
  extends Error {

  constructor(
    readonly status: number,
    readonly detail: string,

    /*
     * 사용자/관리자 공유용 코드.
     * 예: ERR-07949247B3154ABC
     */
    readonly trackingCode:
      string | null = null,

    /*
     * 실제 correlation UUID.
     * 사용자 화면에는 직접 노출하지 않는다.
     */
    readonly requestId:
      string | null = null,
  ) {

    super(
      trackingCode
        ? (
            `${detail} `
            + `(오류 참조번호: ${trackingCode})`
          )
        : detail,
    );


    this.name =
      "ApiRequestError";
  }
}


export function getApiRequestStatus(
  error: unknown,
): number | null {

  return error
    instanceof ApiRequestError
      ? error.status
      : null;
}


export function getApiTrackingCode(
  error: unknown,
): string | null {

  return error
    instanceof ApiRequestError
      ? error.trackingCode
      : null;
}


export function getApiRequestId(
  error: unknown,
): string | null {

  return error
    instanceof ApiRequestError
      ? error.requestId
      : null;
}


export function authenticatedAsset(
  path: string,
) {

  if (/^https?:\/\//i.test(path)) {

    return {
      url: path,
      headers: {},
    };
  }


  const accessToken =
    getAccessToken();


  const headers:
    Record<string, string> = {};


  if (accessToken) {

    headers.Authorization =
      `Bearer ${accessToken}`;
  }


  return {
    url:
      `${baseUrl}${path}`,

    headers,
  };
}


export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {

  const headers =
    new Headers(
      init.headers,
    );


  const accessToken =
    getAccessToken();


  if (
    accessToken
    && !headers.has(
      "Authorization",
    )
  ) {

    headers.set(
      "Authorization",
      `Bearer ${accessToken}`,
    );
  }


  let response:
    Response;


  /*
   * 요청 자체가 서버까지 도달하지 않은 경우.
   *
   * 이 경우 실제 Backend request_id가 없으므로
   * 절대로 가짜 ERR-ID를 생성하지 않는다.
   */
  try {

    response =
      await fetch(
        `${baseUrl}${path}`,
        {
          ...init,
          headers,
        },
      );

  } catch (error) {

    const aborted =
      error instanceof DOMException
      && error.name === "AbortError";


    if (!aborted) {

      notifyOperationalError({
        kind:
          "network",

        status:
          null,

        requestId:
          null,

        trackingCode:
          null,
      });
    }


    throw error;
  }


  if (!response.ok) {

    /*
     * Correlation source of truth.
     *
     * 1. Backend가 직접 발행한 X-Tracking-Code 우선
     * 2. body tracking_code
     * 3. 둘 다 없으면 X-Request-ID에서 동일 규칙으로 생성
     */
    const requestId =
      response.headers.get(
        "X-Request-ID",
      )
      ?? response.headers.get(
        "X-Trace-ID",
      );


    let trackingCode:
      string | null =
        response.headers.get(
          "X-Tracking-Code",
        );


    const body =
      await response.text();


    let detail =
      "요청을 처리하지 못했습니다.";


    try {

      const payload =
        JSON.parse(body) as {

          detail?: unknown;

          error?: {
            message?: unknown;
          };

          tracking_code?: unknown;
        };


      if (
        typeof payload
          .error?.message
        === "string"
      ) {

        detail =
          payload.error.message;
      }

      else if (
        typeof payload.detail
        === "string"
      ) {

        detail =
          payload.detail;
      }


      if (
        typeof payload
          .tracking_code
        === "string"
      ) {

        trackingCode =
          payload.tracking_code;
      }

    } catch {
      /*
       * Backend 원문 오류/HTML/stack 등을
       * 사용자 메시지로 그대로 노출하지 않는다.
       */
    }


    if (!trackingCode) {

      trackingCode =
        trackingCodeFromRequestId(
          requestId,
        );
    }


    /*
     * Validation / 로그인 / 권한 문제는
     * 각 기존 화면의 처리 방식을 유지한다.
     *
     * 운영 장애로 볼 서버 오류만
     * 전역 중앙 팝업을 띄운다.
     */
    if (
      response.status >= 500
    ) {

      notifyOperationalError({
        kind:
          "server",

        status:
          response.status,

        requestId,

        trackingCode,
      });
    }


    throw new ApiRequestError(
      response.status,
      detail,
      trackingCode,
      requestId,
    );
  }


  if (
    response.status === 204
  ) {

    return undefined as T;
  }


  return response.json() as Promise<T>;
}
