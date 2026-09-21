import {
  useState,
} from "react";

import type {
  FormEvent,
} from "react";

import {
  login,
} from "./api";

import {
  saveAuthSession,
} from "./session";

import type {
  LoginResponse,
} from "./types";

import "./login.css";


/* =========================================================
   LoginPage Props
   ========================================================= */

interface LoginPageProps {
  onLoginSuccess: (
    session: LoginResponse,
  ) => void;
}


/* =========================================================
   의료진 로그인 화면
   ========================================================= */

export default function LoginPage({
  onLoginSuccess,
}: LoginPageProps) {

  /* -------------------------------------------------------
     입력값
     ------------------------------------------------------- */

  const [
    loginId,
    setLoginId,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");


  /* -------------------------------------------------------
     비밀번호 표시 여부
     ------------------------------------------------------- */

  const [
    showPassword,
    setShowPassword,
  ] = useState(false);


  /* -------------------------------------------------------
     로그인 요청 상태
     ------------------------------------------------------- */

  const [
    isSubmitting,
    setIsSubmitting,
  ] = useState(false);

  const [
    errorMessage,
    setErrorMessage,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     로그인 요청
     ======================================================== */

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {

    event.preventDefault();


    const normalizedLoginId =
      loginId.trim().toUpperCase();


    if (!normalizedLoginId) {

      setErrorMessage(
        "아이디를 입력해 주세요.",
      );

      return;

    }


    if (!password) {

      setErrorMessage(
        "비밀번호를 입력해 주세요.",
      );

      return;

    }


    setIsSubmitting(true);
    setErrorMessage(null);


    try {

      /**
       * Postman Mock Server 또는
       * 실제 백엔드 로그인 API 호출
       */
      const response =
        await login({
          login_id:
            normalizedLoginId,

          password,
        });


      /**
       * 로그인 응답 저장
       */
      saveAuthSession(
        response,
      );


      /**
       * App 컴포넌트에
       * 로그인 성공 전달
       */
      onLoginSuccess(
        response,
      );

    } catch (error) {

      console.error(
        "로그인 실패:",
        error,
      );


      setErrorMessage(
        "아이디 또는 비밀번호를 확인해 주세요.",
      );

    } finally {

      setIsSubmitting(false);

    }

  }


  return (

    <main className="login-page">

      <div className="login-layout">

        {/* =================================================
            로그인 페이지 - 좌측 서비스 소개 영역
            - BrainOn 브랜드와 의료진 전용 CDSS의 주요 역할 표시
            - 로그인 기능과는 무관한 순수 UI 영역
            ================================================= */}

        <section className="login-introduction">

          <div className="login-introduction-brand">
            <div className="login-introduction-mark" aria-hidden="true">B</div>
            <div>
              <strong>BrainOn</strong>
              <span>Clinical Decision Support System</span>
            </div>
          </div>

          <div className="login-introduction-copy">
            <p className="login-introduction-eyebrow">CLINICAL WORKSPACE</p>
            <h1>
              의료진의 임상 판단을<br />
              <em>더 빠르고 정확하게</em> 지원합니다.
            </h1>
            <p className="login-introduction-description">
              의료영상 분석, 협진, 처방·알림 흐름을 하나로 연결하는<br />
              의료진 전용 CDSS 플랫폼, BrainOn
            </p>
          </div>

          {/* 주요 기능은 장식용 UI이며 별도 클릭 동작을 갖지 않는다. */}
          <div className="login-feature-list" aria-label="BrainOn 주요 기능">
            <div className="login-feature-item">
              <span className="login-feature-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10" /></svg></span>
              <span>영상 분석 지원</span>
            </div>
            <div className="login-feature-item">
              <span className="login-feature-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M7 18H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2v2M10 11a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2l-4 3v-3h-2a2 2 0 0 1-2-2z" /></svg></span>
              <span>협진 워크플로우</span>
            </div>
            <div className="login-feature-item">
              <span className="login-feature-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-4" /></svg></span>
              <span>안전한 진료 지원</span>
            </div>
          </div>

        </section>


        {/* =================================================
            로그인 페이지 - 우측 인증 영역
            - 기존 로그인 API 호출과 세션 저장 로직은 그대로 사용
            - Glass 효과는 이 단일 카드에만 제한하여 적용
            ================================================= */}

        <section className="login-card">

          <div className="login-brand">
            <span className="login-brand-name">BrainOn</span>
            <h2>의료진 로그인</h2>
            <p>계정을 입력하여 BrainOn 업무 화면으로 이동하세요.</p>
          </div>


        {/* ===================================================
            Login Form
            =================================================== */}

          <form className="login-form" onSubmit={handleSubmit}>

          {/* 아이디 */}

            <div className="login-field">

            <label htmlFor="login-id">
              아이디
            </label>

              <div className="login-input-shell">
                <span className="login-input-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg></span>
                <input
                  id="login-id"
                  type="text"
                  placeholder="아이디 입력"
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={loginId}
                  onChange={(event) => setLoginId(event.target.value.toUpperCase())}
                />
              </div>

            </div>


          {/* 비밀번호 */}

            <div className="login-field">

            <label htmlFor="login-password">
              비밀번호
            </label>

              <div className="login-input-shell login-password-field">

                <span className="login-input-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="4" y="10" width="16" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></svg></span>

              <input
                id="login-password"

                type={
                  showPassword
                    ? "text"
                    : "password"
                }

                placeholder="비밀번호 입력"
                autoComplete="current-password"
                value={password}

                onChange={(event) =>
                  setPassword(
                    event.target.value,
                  )
                }
              />


              <button
                type="button"
                className="login-password-toggle"

                onClick={() =>
                  setShowPassword(
                    (previous) =>
                      !previous,
                  )
                }

                aria-label={
                  showPassword
                    ? "비밀번호 숨기기"
                    : "비밀번호 보기"
                }
              >
                {showPassword
                  ? "숨기기"
                  : "보기"}
              </button>

            </div>

            </div>


            {/* 기능이 확정되지 않은 보조 항목은 비활성 UI로만 표시 */}
            <div className="login-form-options">
              <label className="login-remember-option">
                <input type="checkbox" disabled />
                <span>아이디 저장</span>
              </label>
              <button type="button" className="login-support-link" disabled>
                비밀번호 찾기
              </button>
            </div>


          {/* 오류 메시지 */}

            {errorMessage && (

            <p
              className="login-error"
              role="alert"
            >
              {errorMessage}
            </p>

            )}


          {/* 로그인 버튼 */}

            <button
            type="submit"
            className="login-submit-button"

            disabled={
              isSubmitting
            }
          >
            {isSubmitting
              ? "로그인 중..."
              : "로그인"}
            </button>

          </form>


        {/* ===================================================
            안내
            =================================================== */}

          <p className="login-help">
            계정 문의는 병원 시스템 관리자에게 문의하세요.
          </p>

        </section>

      </div>

    </main>

  );

}
