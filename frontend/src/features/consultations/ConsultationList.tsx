import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  FormEvent,
} from "react";

import { getConsultations } from "./api";

import type {
  ConsultationListItem,
  ConsultationListResponse,
  ConsultationPriority,
  ConsultationStatus,
  ConsultationType,
} from "./types";

import "./css/consultation_list.css";


/* =========================================================
   협진 상태 한글 표시
   ========================================================= */

const STATUS_LABEL: Record<
  ConsultationStatus,
  string
> = {
  REQUESTED: "요청됨",
  ACCEPTED: "수락됨",
  IN_PROGRESS: "검토 중",
  RESPONDED: "회신 완료",
  CLOSED: "종결",
  REJECTED: "거절",
  CANCELLED: "취소",
  EXPIRED: "만료",
};


/* =========================================================
   협진 유형
   ========================================================= */

const TYPE_LABEL: Record<
  ConsultationType,
  string
> = {
  RADIOLOGY: "영상의학과",
  NEUROSURGERY: "신경외과",
};


/* =========================================================
   우선순위 화면 표시
   ---------------------------------------------------------
   STAT    → 긴급
   URGENT  → 응급
   ROUTINE → 일반
   ========================================================= */

const PRIORITY_LABEL: Record<
  ConsultationPriority,
  string
> = {
  STAT: "긴급",
  URGENT: "응급",
  ROUTINE: "일반",
};


/* =========================================================
   우선순위 정렬
   ========================================================= */

const PRIORITY_ORDER: Record<
  ConsultationPriority,
  number
> = {
  STAT: 0,
  URGENT: 1,
  ROUTINE: 2,
};


/* =========================================================
   날짜 표시
   ========================================================= */

function formatDateTime(
  value: string,
): string {

  const date =
    new Date(value);


  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }


  return date.toLocaleString(
    "ko-KR",
    {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    },
  );
}


/* =========================================================
   로그인 의료진 기준 상대 의료진
   ========================================================= */

function getCounterpart(
  item: ConsultationListItem,
) {

  if (
    item.viewer_relation ===
    "REQUESTED_BY"
  ) {

    return item.assigned_to;

  }


  return item.requested_by;
}


/* =========================================================
   Filter
   ========================================================= */

interface ConsultationFilters {
  patient: string;
  clinician: string;
  priority: string;
  status: string;
}


const EMPTY_FILTERS: ConsultationFilters = {
  patient: "",
  clinician: "",
  priority: "",
  status: "",
};


/* =========================================================
   협진 목록 Row
   ========================================================= */

interface ConsultationItemProps {
  item: ConsultationListItem;
  number: number;

  onOpenReview?: (
    consultation: ConsultationListItem,
  ) => void;
}

function ConsultationItem({
  item,
  number,
  onOpenReview,
}: ConsultationItemProps) {

  const counterpart =
    getCounterpart(item);


  return (
    <div
      className={
        `consultation-list-item consultation-list-item--${item.priority.toLowerCase()}`
      }
    >

      {/* 번호 */}

      <div className="consultation-list-item__number">
        {number}
      </div>


      {/* 환자 */}

      <div className="consultation-list-item__patient">

        <div className="consultation-list-item__patient-main">

          <strong>
            {item.patient_summary.name}
          </strong>

          <span className="consultation-list-item__patient-no">
            {item.patient_summary.patient_no}
          </span>

        </div>


        <div className="consultation-list-item__patient-sub">

          <span>
            {TYPE_LABEL[item.type]}
          </span>

          <span>
            {item.consultation_id}
          </span>

          <span>
            {item.encounter_id}
          </span>

        </div>

      </div>


      {/* 협진 의료진 */}

      <div className="consultation-list-item__clinician">

        {counterpart ? (
          <>
            <strong>
              {counterpart.name}
            </strong>

            <span>
              {counterpart.department}
            </span>
          </>
        ) : (
          <span className="consultation-list-item__unassigned">
            담당자 미배정
          </span>
        )}

      </div>


      {/* 우선순위 */}

      <div className="consultation-list-item__priority">

        <span
          className={
            `consultation-priority consultation-priority--${item.priority.toLowerCase()}`
          }
        >
          {PRIORITY_LABEL[item.priority]}
        </span>

      </div>


      {/* 상태 */}

      <div className="consultation-list-item__status">

        <span className="consultation-status">
          {
            item.ui_status ||
            STATUS_LABEL[item.status]
          }
        </span>

      </div>


      {/* 요청일시 */}

      <div className="consultation-list-item__date">

        <strong>
          {formatDateTime(item.requested_at)}
        </strong>

      </div>

            {/* ===================================================
          검토
          =================================================== */}

      <div className="consultation-list-item__action">

        <button
          type="button"
          className="consultation-review-button"
          onClick={() => {
                onOpenReview?.(item);
          }}
        >
          검토하기
          <span aria-hidden="true">
            ›
          </span>
        </button>

      </div>


    </div>
  );
}


/* =========================================================
   협진 목록
   ========================================================= */
interface ConsultationListProps {
  onOpenReview?: (
    consultationId: ConsultationListItem,
  ) => void;
}

export default function ConsultationList({
  onOpenReview,
}: ConsultationListProps) {

  const [
    consultations,
    setConsultations,
  ] = useState<ConsultationListResponse>({
    count: 0,
    results: [],
  });


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );


  /* ========================================================
     입력 중인 필터
     ======================================================== */

  const [
    filterInput,
    setFilterInput,
  ] = useState<ConsultationFilters>({
    ...EMPTY_FILTERS,
  });


  /* ========================================================
     실제 검색에 적용된 필터
     ======================================================== */

  const [
    appliedFilters,
    setAppliedFilters,
  ] = useState<ConsultationFilters>({
    ...EMPTY_FILTERS,
  });


  /* ========================================================
     API
     GET /api/v1/consultations
     ======================================================== */

  useEffect(() => {

    let cancelled = false;


    async function loadConsultations() {

      try {

        setLoading(true);
        setError(null);


        const response =
          await getConsultations();


        if (!cancelled) {

          setConsultations(
            response,
          );

        }

      } catch {

        if (!cancelled) {

          setError(
            "협진 목록을 불러오지 못했습니다.",
          );

        }

      } finally {

        if (!cancelled) {

          setLoading(false);

        }

      }

    }


    void loadConsultations();


    return () => {

      cancelled = true;

    };

  }, []);


  /* ========================================================
     협진 의료진 Filter Options
     ---------------------------------------------------------
     Mock 응답에 실제 존재하는 의료진만 Select에 표시
     ======================================================== */

  const clinicianOptions =
    useMemo(
      () => {

        const clinicians =
          new Map<
            string,
            {
              id: string;
              name: string;
              department: string;
            }
          >();


        consultations.results.forEach(
          (item) => {

            const clinician =
              getCounterpart(item);


            if (!clinician) {
              return;
            }


            clinicians.set(
              clinician.id,
              {
                id: clinician.id,
                name: clinician.name,
                department:
                  clinician.department,
              },
            );

          },
        );


        return Array.from(
          clinicians.values(),
        );

      },
      [
        consultations.results,
      ],
    );


  /* ========================================================
     Filtering + Sorting
     ======================================================== */

  const filteredConsultations =
    useMemo(
      () => {

        const patientKeyword =
          appliedFilters.patient
            .trim()
            .toLowerCase();


        const filtered =
          consultations.results.filter(
            (item) => {

              /* -------------------------------
                 환자
                 ------------------------------- */

              const patientMatches =
                patientKeyword.length === 0 ||
                item.patient_summary.name
                  .toLowerCase()
                  .includes(
                    patientKeyword,
                  ) ||
                item.patient_summary.patient_no
                  .toLowerCase()
                  .includes(
                    patientKeyword,
                  );


              /* -------------------------------
                 의료진
                 ------------------------------- */

              const counterpart =
                getCounterpart(item);


              const clinicianMatches =
                appliedFilters.clinician ===
                  "" ||
                counterpart?.id ===
                  appliedFilters.clinician;


              /* -------------------------------
                 Priority
                 ------------------------------- */

              const priorityMatches =
                appliedFilters.priority ===
                  "" ||
                item.priority ===
                  appliedFilters.priority;


              /* -------------------------------
                 Status
                 ------------------------------- */

              const statusMatches =
                appliedFilters.status ===
                  "" ||
                item.status ===
                  appliedFilters.status;


              return (
                patientMatches &&
                clinicianMatches &&
                priorityMatches &&
                statusMatches
              );

            },
          );


        /* -------------------------------------
           긴급 → 응급 → 일반

           같은 Priority이면 최근 요청 우선
           ------------------------------------- */

        return [
          ...filtered,
        ].sort(
          (
            first,
            second,
          ) => {

            const priorityDifference =
              PRIORITY_ORDER[
                first.priority
              ] -
              PRIORITY_ORDER[
                second.priority
              ];


            if (
              priorityDifference !== 0
            ) {

              return priorityDifference;

            }


            return (
              new Date(
                second.requested_at,
              ).getTime() -
              new Date(
                first.requested_at,
              ).getTime()
            );

          },
        );

      },
      [
        consultations.results,
        appliedFilters,
      ],
    );


  /* ========================================================
     검색
     ======================================================== */

  const handleSearch = (
    event: FormEvent<HTMLFormElement>,
  ) => {

    event.preventDefault();


    setAppliedFilters({
      ...filterInput,
    });

  };


  /* ========================================================
     초기화
     ======================================================== */

  const handleReset = () => {

    setFilterInput({
      ...EMPTY_FILTERS,
    });


    setAppliedFilters({
      ...EMPTY_FILTERS,
    });

  };


  return (
    <section className="consultation-list">

      {/* =====================================================
          PAGE TITLE
          ===================================================== */}

      <header className="consultation-list__header">

        <span className="consultation-list__eyebrow">
          CONSULTATION
        </span>


        <div className="consultation-list__title-row">

          <h1>
            협진 목록
          </h1>


          <span className="consultation-list__title-count">
            {filteredConsultations.length}건
          </span>

        </div>


        <p>
          요청하거나 배정된 협진 업무의
          현재 진행 상태를 확인합니다.
        </p>

      </header>


      {/* =====================================================
          FILTER
          ===================================================== */}

      <form
        className="consultation-list__filter"
        onSubmit={
          handleSearch
        }
      >

        {/* 환자 */}

        <label className="consultation-filter-field">

          <span>
            환자명
          </span>


          <input
            type="text"
            value={
              filterInput.patient
            }
            placeholder="환자명 또는 등록번호"
            onChange={
              (event) => {

                setFilterInput(
                  (previous) => ({
                    ...previous,
                    patient:
                      event.target.value,
                  }),
                );

              }
            }
          />

        </label>


        {/* 협진 의료진 */}

        <label className="consultation-filter-field">

          <span>
            협진 의료진
          </span>


          <select
            value={
              filterInput.clinician
            }
            onChange={
              (event) => {

                setFilterInput(
                  (previous) => ({
                    ...previous,
                    clinician:
                      event.target.value,
                  }),
                );

              }
            }
          >

            <option value="">
              전체
            </option>


            {
              clinicianOptions.map(
                (clinician) => (

                  <option
                    key={
                      clinician.id
                    }
                    value={
                      clinician.id
                    }
                  >
                    {
                      `${clinician.name} · ${clinician.department}`
                    }
                  </option>

                ),
              )
            }

          </select>

        </label>


        {/* 우선순위 */}

        <label className="consultation-filter-field">

          <span>
            우선순위
          </span>


          <select
            value={
              filterInput.priority
            }
            onChange={
              (event) => {

                setFilterInput(
                  (previous) => ({
                    ...previous,
                    priority:
                      event.target.value,
                  }),
                );

              }
            }
          >

            <option value="">
              전체
            </option>

            <option value="STAT">
              긴급
            </option>

            <option value="URGENT">
              응급
            </option>

            <option value="ROUTINE">
              일반
            </option>

          </select>

        </label>


        {/* 상태 */}

        <label className="consultation-filter-field">

          <span>
            상태
          </span>


          <select
            value={
              filterInput.status
            }
            onChange={
              (event) => {

                setFilterInput(
                  (previous) => ({
                    ...previous,
                    status:
                      event.target.value,
                  }),
                );

              }
            }
          >

            <option value="">
              전체
            </option>


            {
              Object.entries(
                STATUS_LABEL,
              ).map(
                ([
                  status,
                  label,
                ]) => (

                  <option
                    key={
                      status
                    }
                    value={
                      status
                    }
                  >
                    {label}
                  </option>

                ),
              )
            }

          </select>

        </label>


        {/* 버튼 */}

        <div className="consultation-filter-actions">

          <button
            type="button"
            className="consultation-filter-reset"
            onClick={
              handleReset
            }
          >
            초기화
          </button>


          <button
            type="submit"
            className="consultation-filter-search"
          >
            검색
          </button>

        </div>

      </form>


      {/* =====================================================
          TABLE
          ===================================================== */}

      <div className="consultation-list__card">

        {/* Column Header */}

        <div className="consultation-list__column-header">

          <span>
            번호
          </span>

          <span>
            환자
          </span>

          <span>
            협진 의료진
          </span>

          <span>
            우선순위
          </span>

          <span>
            상태
          </span>

          <span>
            요청일시
          </span>

          <span>
            검토
          </span>

        </div>


        {/* Loading */}

        {loading && (

          <div className="consultation-list__message">
            협진 목록을 불러오는 중입니다.
          </div>

        )}


        {/* Error */}

        {!loading &&
          error && (

            <div className="consultation-list__message consultation-list__message--error">
              {error}
            </div>

          )}


        {/* Empty */}

        {!loading &&
          !error &&
          filteredConsultations.length ===
            0 && (

            <div className="consultation-list__message">
              조건에 해당하는 협진 업무가 없습니다.
            </div>

          )}


        {/* Rows */}

        {!loading &&
          !error &&
          filteredConsultations.length >
            0 && (

            <div className="consultation-list__items">

              {
                filteredConsultations.map(
                  (
                    item,
                    index,
                  ) => (

                    <ConsultationItem
                      key={
                        item.consultation_id
                      }
                      item={
                        item
                      }
                      number={
                        index + 1
                      }

                      onOpenReview={
                        onOpenReview
                      }
                    />

                  ),
                )
              }

            </div>

          )}

      </div>

    </section>
  );
}