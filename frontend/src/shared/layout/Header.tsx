import {
  useEffect,
  useState,
} from "react";

import type {
  FormEvent,
} from "react";

import { getPatients } from "../../features/patients/api";
import type { Patient } from "../../features/patients/types";

import {
  getNotifications,
} from "../../features/notifications/api";

import {
  NOTIFICATION_STATE_CHANGED_EVENT,
} from "../../features/notifications/events";
import type { LoginUser } from "../../features/auth/types";
import NotificationPopover from "../../features/notifications/NotificationPopover";
import type {
  NotificationItem,
} from "../../features/notifications/types";

import "./layout.css";


/* =========================================================
   Header Props

   환자를 선택하면 AppShell로 Patient 객체를 전달한다.
   다음 단계에서 이 값을 이용해
   [환자명 | Chart ×] 탭을 만들 예정이다.
   ========================================================= */

interface HeaderProps {
  onPatientSelect?: (patient: Patient) => void;
  onNotificationsOpen: () => void;
  onNotificationRelatedWork?: (
    item: NotificationItem,
  ) => Promise<boolean>;
  currentUser: LoginUser;
  onLogout: () => void;
}


/**
 * 의료진 Web 공통 Header
 *
 * 환자 검색 동작
 * ---------------------------------------------------------
 *
 * 1. 한 글자부터 자동완성
 * 2. 이름 / patient_no 포함 검색
 * 3. 최대 5명 표시
 * 4. 환자 클릭
 *    → Dropdown 닫기
 *    → 검색창에 "이름 · 등록번호" 유지
 * 5. 검색창을 다시 수정하면
 *    → 선택 상태 해제
 *    → 자동완성 다시 시작
 */
export default function Header({
  onPatientSelect,
  onNotificationsOpen,
  onNotificationRelatedWork,
  currentUser,
  onLogout,
}: HeaderProps) {

  /* ========================================================
     1. Light / Dark Theme
     ======================================================== */

  const [theme, setTheme] =
    useState<"light" | "dark">(() => {
      const savedTheme =
        localStorage.getItem("brain-cdss-theme");

      return savedTheme === "dark"
        ? "dark"
        : "light";
    });


  /* ========================================================
     2. 환자 검색 상태
     ======================================================== */

  /**
   * 검색창에 표시되는 값
   *
   * 검색 중:
   * 김
   * 김준
   * P000
   *
   * 환자 선택 후:
   * 김준수 · P000001
   */
  const [searchKeyword, setSearchKeyword] =
    useState("");


  /**
   * 기존 Mock API에서 받아온 환자 목록
   */
  const [patients, setPatients] =
    useState<Patient[]>([]);


  /**
   * 현재 검색어에 맞는 자동완성 결과
   */
  const [searchResults, setSearchResults] =
    useState<Patient[]>([]);


  /**
   * Dropdown 표시 여부
   */
  const [isSearchOpen, setIsSearchOpen] =
    useState(false);


  /**
   * 환자 데이터를 이미 가져왔는지 여부
   *
   * true라면 같은 화면에서
   * Mock API를 계속 반복 호출하지 않는다.
   */
  const [
    hasLoadedPatients,
    setHasLoadedPatients,
  ] = useState(false);


  /**
   * API 요청 중 여부
   */
  const [isSearching, setIsSearching] =
    useState(false);


  /**
   * API 오류 메시지
   */
  const [searchError, setSearchError] =
    useState<string | null>(null);


  /**
   * 현재 환자가 선택된 상태인지 여부
   *
   * true
   * → 검색창에 선택한 환자가 표시됨
   * → 자동완성은 닫힘
   *
   * 사용자가 검색창을 다시 수정하면
   * false로 변경된다.
   */
  const [
    isPatientSelected,
    setIsPatientSelected,
  ] = useState(false);


  /* ========================================================
     3. Theme
     ======================================================== */

  useEffect(() => {
    document.documentElement.dataset.theme =
      theme;

    localStorage.setItem(
      "brain-cdss-theme",
      theme,
    );
  }, [theme]);


  function toggleTheme() {
    setTheme((currentTheme) =>
      currentTheme === "light"
        ? "dark"
        : "light",
    );
  }


  /* ========================================================
     4. 환자 목록 API 조회
     ======================================================== */

  useEffect(() => {
    const keyword =
      searchKeyword.trim();


    /**
     * 환자를 선택한 상태라면
     * 선택된 환자 문자열을 검색어로 처리하지 않는다.
     */
    if (isPatientSelected) {
      return;
    }


    /**
     * 아무것도 입력하지 않았다면
     * 검색하지 않는다.
     */
    if (keyword.length < 1) {
      setSearchResults([]);
      setSearchError(null);
      setIsSearchOpen(false);

      return;
    }


    /**
     * 이미 환자 목록을 가져왔다면
     * API 재호출 필요 없음
     */
    if (hasLoadedPatients) {
      return;
    }


    async function loadPatients() {
      setIsSearching(true);
      setSearchError(null);

      try {
        /**
         * 기존 Postman Mock Server
         *
         * GET /api/v1/patients
         */
        const response =
          await getPatients();


        setPatients(
          response.results,
        );

        setHasLoadedPatients(true);
      } catch (error) {
        console.error(
          "환자 목록 조회 실패:",
          error,
        );

        setSearchError(
          "환자 정보를 불러오지 못했습니다.",
        );

        setIsSearchOpen(true);
      } finally {
        setIsSearching(false);
      }
    }


    void loadPatients();
  }, [
    searchKeyword,
    hasLoadedPatients,
    isPatientSelected,
  ]);


  /* ========================================================
     5. 자동완성
     ======================================================== */

  useEffect(() => {
    const keyword =
      searchKeyword.trim();


    /**
     * 환자를 선택한 상태
     *
     * 검색창에는
     * "김준수 · P000001"
     *
     * 을 그대로 보여주고
     * Dropdown은 닫는다.
     */
    if (isPatientSelected) {
      setIsSearchOpen(false);

      return;
    }


    /**
     * 검색어가 없으면 닫는다.
     */
    if (keyword.length < 1) {
      setSearchResults([]);
      setIsSearchOpen(false);

      return;
    }


    /**
     * 아직 환자 API 응답이 오지 않았다면
     * 기다린다.
     */
    if (!hasLoadedPatients) {
      return;
    }


    const normalizedKeyword =
      keyword.toLowerCase();


    /**
     * 이름 또는 등록번호 어디에든
     * 검색어가 포함되면 검색된다.
     *
     * 예:
     *
     * 검색어 "김"
     *
     * 김준수 → O
     * 박김영 → O
     * 이수김 → O
     */
    const filteredPatients =
      patients

        .filter((patient) => {
          const patientName =
            patient.name.toLowerCase();

          const patientNumber =
            patient.patient_no.toLowerCase();


          return (
            patientName.includes(
              normalizedKeyword,
            ) ||
            patientNumber.includes(
              normalizedKeyword,
            )
          );
        })


        /**
         * 자동완성 최대 표시 개수
         *
         * 현재 최대 5명
         */
        .slice(0, 5);


    setSearchResults(
      filteredPatients,
    );

    setSearchError(null);

    setIsSearchOpen(true);
  }, [
    searchKeyword,
    patients,
    hasLoadedPatients,
    isPatientSelected,
  ]);


  /* ========================================================
     6. 환자 선택
     ======================================================== */

  function handleSelectPatient(
    patient: Patient,
  ) {

    /**
     * Dropdown 닫기
     */
    setIsSearchOpen(false);


    /**
     * 기존 자동완성 결과 제거
     */
    setSearchResults([]);


    /**
     * 현재 환자가 선택됐음을 기록
     */
    setIsPatientSelected(true);


    /**
     * 검색창에는 선택한 환자 정보를
     * 계속 남겨둔다.
     *
     * 예:
     *
     * 김준수 · P000001
     */
    setSearchKeyword(
      `${patient.name} · ${patient.patient_no}`,
    );


    /**
     * 선택한 Patient 객체를
     * AppShell로 전달
     */
    onPatientSelect?.(patient);
  }


  /* ========================================================
     7. Enter / 검색 버튼
     ======================================================== */

  function handleSearchSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();


    /**
     * 이미 환자를 선택한 상태에서는
     * Enter를 눌러도 다시 검색하지 않는다.
     */
    if (isPatientSelected) {
      return;
    }


    /**
     * 검색 결과가 정확히 1명
     *
     * → Enter / 검색 버튼으로 바로 선택
     */
    if (searchResults.length === 1) {
      handleSelectPatient(
        searchResults[0],
      );

      return;
    }


    /**
     * 여러 명이면
     * 첫 환자를 임의 선택하지 않는다.
     *
     * Dropdown을 유지해서
     * 사용자가 직접 고르게 한다.
     */
    if (searchResults.length > 1) {
      setIsSearchOpen(true);

      return;
    }


    /**
     * 검색 결과가 0명인 경우에도
     * "검색된 환자가 없습니다."를 보여준다.
     */
    setIsSearchOpen(true);
  }


  const [
    unreadNotificationCount,
    setUnreadNotificationCount,
  ] = useState(0);


  useEffect(() => {
    let active = true;

    async function refreshUnreadNotifications() {
      try {
        const response =
          await getNotifications({
            unreadOnly: true,
          });

        if (active) {
          setUnreadNotificationCount(
            response.unread_count ?? 0,
          );
        }
      } catch (error) {
        console.error(
          "UNREAD_NOTIFICATION_COUNT_FAILED",
          error,
        );
      }
    }

    function handleNotificationChanged() {
      void refreshUnreadNotifications();
    }

    function handleVisibilityChange() {
      if (
        document.visibilityState ===
        "visible"
      ) {
        void refreshUnreadNotifications();
      }
    }

    void refreshUnreadNotifications();

    const intervalId =
      window.setInterval(
        () => {
          void refreshUnreadNotifications();
        },
        5000,
      );

    window.addEventListener(
      NOTIFICATION_STATE_CHANGED_EVENT,
      handleNotificationChanged,
    );

    window.addEventListener(
      "focus",
      handleNotificationChanged,
    );

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange,
    );

    return () => {
      active = false;

      window.clearInterval(
        intervalId,
      );

      window.removeEventListener(
        NOTIFICATION_STATE_CHANGED_EVENT,
        handleNotificationChanged,
      );

      window.removeEventListener(
        "focus",
        handleNotificationChanged,
      );

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange,
      );
    };
  }, [currentUser.id]);


  return (
    <header className="header">

      {/* =====================================================
          1. Brand
          ===================================================== */}

      <div className="header-brand-slot">

        <div className="header-product">

          <div className="brand-mark">
            B
          </div>

          <div className="header-product-text">

            <strong>
              Brain CDSS
            </strong>

            <span>
              Clinical Decision Support
            </span>

          </div>

        </div>

      </div>


      {/* =====================================================
          2. Header Main
          ===================================================== */}

      <div className="header-main-area">

        {/* 소속 기관 */}

        <button
          type="button"
          className="header-organization"
        >
          {currentUser.hospital?.name ?? "소속 기관"}

          <span>
            ⌄
          </span>
        </button>


        {/* ===================================================
            3. 환자 통합 검색
            =================================================== */}

        <div className="header-patient-search-area">

          <form
            className="header-search"
            onSubmit={handleSearchSubmit}
          >

            <input
              type="search"

              placeholder="환자 검색 (이름, 등록번호)"

              aria-label="환자 통합 검색"

              value={searchKeyword}

              onChange={(event) => {
                /**
                 * 사용자가 검색창 내용을 수정하기 시작하면
                 * 이전 환자 선택 상태를 해제한다.
                 *
                 * 그러면 자동완성이 다시 시작된다.
                 */
                if (isPatientSelected) {
                  setIsPatientSelected(false);
                }


                setSearchKeyword(
                  event.target.value,
                );
              }}
            />


            <button
              type="submit"
              className="header-search-button"
              aria-label="환자 검색"
              disabled={isSearching}
            >
              {isSearching
                ? "검색 중"
                : "검색"}
            </button>

          </form>


          {/* =================================================
              자동완성 Dropdown
              ================================================= */}

          {isSearchOpen && (

            <div className="header-search-dropdown">

              {searchError ? (

                <div className="header-search-message">
                  {searchError}
                </div>

              ) : searchResults.length === 0 ? (

                <div className="header-search-message">
                  검색된 환자가 없습니다.
                </div>

              ) : (

                searchResults.map(
                  (patient) => (

                    <button
                      key={patient.id}
                      type="button"
                      className="header-search-result"

                      onClick={() =>
                        handleSelectPatient(
                          patient,
                        )
                      }
                    >

                      <strong>
                        {patient.name}
                      </strong>

                      <span>
                        {patient.patient_no}
                      </span>

                    </button>

                  ),
                )

              )}

            </div>

          )}

        </div>


        {/* ===================================================
            4. 오른쪽 사용자 영역
            =================================================== */}

        <div className="header-actions">

          <NotificationPopover
              unreadCount={
                unreadNotificationCount
              }
              onOpenCenter={
                onNotificationsOpen
              }
              onOpenRelatedWork={
                onNotificationRelatedWork
              }
            />


          <button
            type="button"
            className="header-icon-button theme-toggle"
            onClick={toggleTheme}
            aria-label={
              theme === "light"
                ? "다크 모드로 변경"
                : "라이트 모드로 변경"
            }
          >
            {theme === "light"
              ? "🌙"
              : "☀️"}
          </button>


          <div className="user-info">

            <div className="user-avatar">
              {currentUser.name.slice(0, 2)}
            </div>

            <div className="user-text">

              <strong>
                {currentUser.name}
              </strong>

              <span>
                {currentUser.role.name}
              </span>

            </div>

          </div>


          <button
            type="button"
            className="header-logout-button"
            onClick={onLogout}
          >
            로그아웃
          </button>

            <span className="user-menu-arrow">
              ⌄
            </span>

          </div>

        </div>

    </header>
  );
}