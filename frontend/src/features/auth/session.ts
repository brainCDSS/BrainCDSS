import type {
  LoginResponse,
} from "./types";


/* =========================================================
   로그인 세션 저장 Key
   ========================================================= */

const AUTH_SESSION_KEY =
  "brain-cdss-auth-session";


/* =========================================================
   로그인 성공 정보 저장
   ---------------------------------------------------------
   access, refresh, user 응답을 sessionStorage에 저장한다.
   ========================================================= */

export function saveAuthSession(
  session: LoginResponse,
) {

  sessionStorage.setItem(
    AUTH_SESSION_KEY,
    JSON.stringify(session),
  );

}


/* =========================================================
   저장된 로그인 정보 불러오기
   ========================================================= */

export function loadAuthSession():
  LoginResponse | null {

  const storedSession =
    sessionStorage.getItem(
      AUTH_SESSION_KEY,
    );


  if (!storedSession) {
    return null;
  }


  try {

    const parsedSession =
      JSON.parse(
        storedSession,
      ) as LoginResponse;


    /**
     * 최소한의 필수값이 없으면
     * 정상 로그인 세션으로 사용하지 않는다.
     */
    if (
      !parsedSession.access ||
      !parsedSession.refresh ||
      !parsedSession.user
    ) {

      clearAuthSession();

      return null;

    }


    return parsedSession;

  } catch {

    /**
     * 저장된 값이 정상 JSON이 아니면
     * 삭제하고 로그아웃 상태로 처리한다.
     */
    clearAuthSession();

    return null;

  }

}


/* =========================================================
   Access Token 조회
   ---------------------------------------------------------
   이후 인증이 필요한 API 요청의
   Authorization Header에 사용한다.
   ========================================================= */

export function getAccessToken():
  string | null {

  return loadAuthSession()?.access ?? null;

}


/* =========================================================
   로그인 정보 삭제
   ---------------------------------------------------------
   로그아웃할 때 사용한다.
   ========================================================= */

export function clearAuthSession() {

  sessionStorage.removeItem(
    AUTH_SESSION_KEY,
  );

}