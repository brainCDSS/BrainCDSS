import {
  useState,
} from "react";

import {
  getAuditLogs,
} from "./api";

import type {
  AuditLogItem,
} from "./types";

import "./admin.css";


export default function AuditLogPage() {
  const [
    reason,
    setReason,
  ] = useState("");

  const [
    trackingCode,
    setTrackingCode,
  ] = useState("");

  const [
    from,
    setFrom,
  ] = useState("");

  const [
    to,
    setTo,
  ] = useState("");

  const [
    actor,
    setActor,
  ] = useState("");

  const [
    role,
    setRole,
  ] = useState("");

  const [
    action,
    setAction,
  ] = useState("");

  const [
    outcome,
    setOutcome,
  ] = useState("");

  const [
    rows,
    setRows,
  ] = useState<
    AuditLogItem[]
  >([]);

  const [
    error,
    setError,
  ] = useState("");


  const load = () => {

    if (
      reason.trim().length < 5
    ) {
      setError(
        "조회 사유를 5자 이상 입력해 주세요.",
      );

      return;
    }


    if (
      (from && !to)
      || (!from && to)
    ) {
      setError(
        "시작일과 종료일을 함께 입력해 주세요.",
      );

      return;
    }


    const normalizedTrackingCode =
      trackingCode
        .trim()
        .toUpperCase();


    if (
      normalizedTrackingCode
      && !/^ERR-[0-9A-F]{16}$/.test(
        normalizedTrackingCode,
      )
    ) {
      setError(
        "오류 참조번호 형식이 올바르지 않습니다.",
      );

      return;
    }


    const params =
      new URLSearchParams({
        reason:
          reason.trim(),
      });


    if (
      normalizedTrackingCode
    ) {
      params.set(
        "tracking_code",
        normalizedTrackingCode,
      );
    }


    if (
      from
      && to
    ) {
      params.set(
        "occurred_from",
        new Date(
          `${from}T00:00:00`,
        ).toISOString(),
      );

      params.set(
        "occurred_to",
        new Date(
          `${to}T23:59:59`,
        ).toISOString(),
      );
    }


    if (actor) {
      params.set(
        "actor_login_id",
        actor,
      );
    }

    if (role) {
      params.set(
        "actor_role_code",
        role,
      );
    }

    if (action) {
      params.set(
        "action",
        action,
      );
    }

    if (outcome) {
      params.set(
        "outcome",
        outcome,
      );
    }


    getAuditLogs(
      params,
    )
      .then(
        (response) => {
          setRows(
            response.results,
          );

          setError("");
        },
      )
      .catch(
        () => {
          setError(
            "감사 로그를 불러오지 못했습니다.",
          );
        },
      );
  };


  return (
    <section
      className="
        clinical-page
        admin-page
      "
    >
      <header
        className="
          clinical-page__heading
        "
      >
        <h2>
          감사 로그
        </h2>

        <p>
          감사 목적의 시스템 접근·작업 이력과
          오류 참조번호를 조회합니다.
        </p>
      </header>


      <div
        className="
          clinical-toolbar
          admin-filter-grid
        "
      >
        <label>
          조회 사유

          <input
            value={reason}
            onChange={
              (event) =>
                setReason(
                  event.target.value,
                )
            }
            placeholder="필수, 5자 이상"
          />
        </label>


        <label>
          오류 참조번호

          <input
            value={
              trackingCode
            }
            onChange={
              (event) =>
                setTrackingCode(
                  event.target.value,
                )
            }
            placeholder="ERR-9D47C68E4A2342EA"
          />
        </label>


        <label>
          시작일

          <input
            type="date"
            value={from}
            onChange={
              (event) =>
                setFrom(
                  event.target.value,
                )
            }
          />
        </label>


        <label>
          종료일

          <input
            type="date"
            value={to}
            onChange={
              (event) =>
                setTo(
                  event.target.value,
                )
            }
          />
        </label>


        <label>
          사용자

          <input
            value={actor}
            onChange={
              (event) =>
                setActor(
                  event.target.value,
                )
            }
          />
        </label>


        <label>
          Role

          <input
            value={role}
            onChange={
              (event) =>
                setRole(
                  event.target.value,
                )
            }
          />
        </label>


        <label>
          작업 유형

          <input
            value={action}
            onChange={
              (event) =>
                setAction(
                  event.target.value,
                )
            }
          />
        </label>


        <label>
          결과

          <select
            value={outcome}
            onChange={
              (event) =>
                setOutcome(
                  event.target.value,
                )
            }
          >
            <option value="">
              전체
            </option>

            <option value="SUCCESS">
              SUCCESS
            </option>

            <option value="FAILURE">
              FAILURE
            </option>
          </select>
        </label>


        <button
          type="button"
          onClick={load}
        >
          조회
        </button>
      </div>


      {error && (
        <div
          className="
            clinical-card
          "
        >
          <div
            className="
              clinical-state
              clinical-state--error
            "
          >
            {error}
          </div>
        </div>
      )}


      <div
        className="
          clinical-card
          clinical-table-wrap
        "
      >
        <table
          className="
            clinical-table
          "
        >
          <thead>
            <tr>
              <th>시간</th>
              <th>오류 참조번호</th>
              <th>사용자</th>
              <th>Role</th>
              <th>작업</th>
              <th>대상</th>
              <th>결과</th>
            </tr>
          </thead>

          <tbody>
            {
              rows.map(
                (row) => (
                  <tr
                    key={
                      row.audit_id
                    }
                  >
                    <td>
                      {
                        new Date(
                          row.occurred_at,
                        ).toLocaleString()
                      }
                    </td>

                    <td>
                      <code>
                        {
                          row.tracking_code
                          || "-"
                        }
                      </code>
                    </td>

                    <td>
                      {
                        row.actor_login_id
                        ?? "-"
                      }
                    </td>

                    <td>
                      {
                        row.actor_role_code
                        ?? "-"
                      }
                    </td>

                    <td>
                      {row.action}
                    </td>

                    <td>
                      {row.resource_type}
                      {" "}
                      {
                        row.resource_id
                        ?? ""
                      }
                    </td>

                    <td>
                      {row.outcome}
                    </td>
                  </tr>
                ),
              )
            }


            {
              rows.length === 0
              && (
                <tr>
                  <td
                    colSpan={7}
                    className="
                      admin-table-empty
                    "
                  >
                    조회 조건과 사유를
                    입력한 뒤 조회해 주세요.
                  </td>
                </tr>
              )
            }
          </tbody>
        </table>
      </div>
    </section>
  );
}
