import {
  useEffect,
  useState,
} from "react";

import {
  OPERATIONAL_ERROR_EVENT,
  type OperationalErrorPayload,
} from "./operationalError";

import "./operational-error.css";


export default function OperationalErrorHost() {

  const [
    error,
    setError,
  ] =
    useState<
      OperationalErrorPayload
      | null
    >(null);


  useEffect(() => {

    const handleOperationalError = (
      event: Event,
    ) => {

      const customEvent =
        event as CustomEvent<
          OperationalErrorPayload
        >;


      setError(
        customEvent.detail,
      );
    };


    window.addEventListener(
      OPERATIONAL_ERROR_EVENT,
      handleOperationalError,
    );


    return () => {

      window.removeEventListener(
        OPERATIONAL_ERROR_EVENT,
        handleOperationalError,
      );
    };

  }, []);


  if (!error) {
    return null;
  }


  const networkError =
    error.kind === "network";


  return (
    <div
      className="operational-error-overlay"
      role="presentation"
    >
      <section
        className="operational-error-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="operational-error-title"
      >

        <div
          className="operational-error-icon"
          aria-hidden="true"
        >
          !
        </div>


        <h2
          id="operational-error-title"
          className="operational-error-title"
        >
          {
            networkError
              ? "서버에 연결할 수 없습니다"
              : "요청을 처리할 수 없습니다"
          }
        </h2>


        <p
          className="operational-error-message"
        >
          {
            networkError ? (
              <>
                서버 연결 중 문제가 발생했습니다.
                <br />
                잠시 후 다시 시도해 주세요.
              </>
            ) : (
              <>
                처리 중 오류가 발생했습니다.
                <br />
                문제가 계속되면 관리자에게 문의해 주세요.
              </>
            )
          }
        </p>


        {
          !networkError && (
            <div
              className="operational-error-reference"
            >
              <span>
                오류 참조번호
              </span>

              <strong>
                {
                  error.trackingCode
                  ?? "확인 불가"
                }
              </strong>
            </div>
          )
        }


        <button
          type="button"
          className="operational-error-close"
          onClick={() =>
            setError(null)
          }
        >
          확인
        </button>

      </section>
    </div>
  );
}
