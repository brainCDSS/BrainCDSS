import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  getNotifications,
  markNotificationRead,
} from "./api";

import {
  emitNotificationStateChanged,
  NOTIFICATION_STATE_CHANGED_EVENT,
} from "./events";

import type {
  NotificationItem,
} from "./types";

import "./notification_popover.css";


interface NotificationPopoverProps {
  unreadCount: number;

  onOpenCenter: () => void;

  onOpenRelatedWork?: (
    item: NotificationItem,
  ) => Promise<boolean>;
}


const MAX_RECENT_NOTIFICATIONS = 5;


function formatDate(
  value: string,
): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const diffMs =
    Date.now() - date.getTime();

  const minute =
    60 * 1000;

  const hour =
    60 * minute;

  const day =
    24 * hour;

  if (diffMs < minute) {
    return "방금";
  }

  if (diffMs < hour) {
    return `${Math.floor(diffMs / minute)}분 전`;
  }

  if (diffMs < day) {
    return `${Math.floor(diffMs / hour)}시간 전`;
  }

  return date.toLocaleDateString(
    "ko-KR",
  );
}


function categoryLabel(
  category: string,
): string {
  const labels: Record<string, string> = {
    EMERGENCY: "응급",
    CONSULTATION: "협진",
    IMAGING: "검사·영상",
    AI_ANALYSIS: "AI 분석",
    APPOINTMENT: "예약",
    SYSTEM: "시스템",
  };

  return labels[category] ?? category;
}


export default function NotificationPopover({
  unreadCount,
  onOpenCenter,
  onOpenRelatedWork,
}: NotificationPopoverProps) {
  const [
    open,
    setOpen,
  ] = useState(false);

  const [
    items,
    setItems,
  ] = useState<NotificationItem[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const rootRef =
    useRef<HTMLDivElement | null>(
      null,
    );


  const refresh =
    useCallback(
      async () => {
        setLoading(true);

        try {
          const response =
            await getNotifications();

          const results =
            Array.isArray(
              response.results,
            )
              ? response.results
              : [];

          setItems(
            results.slice(
              0,
              MAX_RECENT_NOTIFICATIONS,
            ),
          );

          setError(null);
        } catch (requestError) {
          console.error(
            "NOTIFICATION_POPOVER_LOAD_FAILED",
            requestError,
          );

          setError(
            "최근 알림을 불러오지 못했습니다.",
          );
        } finally {
          setLoading(false);
        }
      },
      [],
    );


  useEffect(
    () => {
      if (open) {
        void refresh();
      }
    },
    [
      open,
      refresh,
    ],
  );


  useEffect(
    () => {
      const handleNotificationChange =
        () => {
          if (open) {
            void refresh();
          }
        };

      window.addEventListener(
        NOTIFICATION_STATE_CHANGED_EVENT,
        handleNotificationChange,
      );

      return () => {
        window.removeEventListener(
          NOTIFICATION_STATE_CHANGED_EVENT,
          handleNotificationChange,
        );
      };
    },
    [
      open,
      refresh,
    ],
  );


  useEffect(
    () => {
      if (!open) {
        return;
      }

      const handlePointerDown =
        (event: MouseEvent) => {
          const target =
            event.target as Node | null;

          if (
            target &&
            !rootRef.current?.contains(
              target,
            )
          ) {
            setOpen(false);
          }
        };

      document.addEventListener(
        "mousedown",
        handlePointerDown,
      );

      return () => {
        document.removeEventListener(
          "mousedown",
          handlePointerDown,
        );
      };
    },
    [
      open,
    ],
  );


  async function ensureRead(
    item: NotificationItem,
  ): Promise<NotificationItem> {
    if (item.is_read) {
      return item;
    }

    try {
      const result =
        await markNotificationRead(
          item.id,
        );

      const next: NotificationItem = {
        ...item,
        ...result,
        is_read: true,
      };

      setItems(
        (current) =>
          current.map(
            (entry) =>
              entry.id === item.id
                ? next
                : entry,
          ),
      );

      emitNotificationStateChanged();

      return next;
    } catch (requestError) {
      console.error(
        "NOTIFICATION_POPOVER_READ_FAILED",
        requestError,
      );

      return item;
    }
  }


  async function openNotification(
    item: NotificationItem,
  ) {
    const target =
      await ensureRead(
        item,
      );

    sessionStorage.setItem(
      "brainon-notification-focus-id",
      target.id,
    );

    setOpen(false);

    onOpenCenter();
  }


  async function openRelatedWork(
    item: NotificationItem,
  ) {
    const target =
      await ensureRead(
        item,
      );

    if (!onOpenRelatedWork) {
      sessionStorage.setItem(
        "brainon-notification-focus-id",
        target.id,
      );

      setOpen(false);

      onOpenCenter();

      return;
    }

    try {
      const opened =
        await onOpenRelatedWork(
          target,
        );

      if (opened) {
        setOpen(false);

        return;
      }

      sessionStorage.setItem(
        "brainon-notification-focus-id",
        target.id,
      );

      setOpen(false);

      onOpenCenter();
    } catch (requestError) {
      console.error(
        "NOTIFICATION_POPOVER_RELATED_WORK_FAILED",
        requestError,
      );

      sessionStorage.setItem(
        "brainon-notification-focus-id",
        target.id,
      );

      setOpen(false);

      onOpenCenter();
    }
  }


  return (
    <div
      className="header-notification-popover"
      ref={rootRef}
    >
      <button
        type="button"
        className={[
          "header-notification-trigger",
          unreadCount > 0
            ? "has-unread"
            : "",
        ].join(" ")}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={
          unreadCount > 0
            ? `알림, 읽지 않은 알림 ${unreadCount}건`
            : "알림"
        }
        onClick={() =>
          setOpen(
            (value) => !value,
          )
        }
      >
        <span>알림</span>

        {unreadCount > 0 && (
          <span
            className="header-notification-dot"
            aria-hidden="true"
          />
        )}

        {unreadCount > 0 && (
          <strong className="header-notification-count">
            {unreadCount > 99
              ? "99+"
              : unreadCount}
          </strong>
        )}
      </button>

      {open && (
        <section
          className="notification-popover-panel"
          role="dialog"
          aria-label="최근 알림"
        >
          <header className="notification-popover-header">
            <div>
              <strong>최근 알림</strong>

              <span>
                미확인 {unreadCount}건
              </span>
            </div>
          </header>

          <div className="notification-popover-body">
            {loading ? (
              <div className="notification-popover-state">
                불러오는 중...
              </div>
            ) : error ? (
              <div
                className="notification-popover-state is-error"
                role="alert"
              >
                {error}
              </div>
            ) : !items.length ? (
              <div className="notification-popover-state">
                최근 알림이 없습니다.
              </div>
            ) : (
              items.map(
                (item) => (
                  <article
                    key={item.id}
                    className={[
                      "notification-popover-item",
                      item.is_read
                        ? ""
                        : "is-unread",
                    ].join(" ")}
                  >
                    <button
                      type="button"
                      className="notification-popover-item-main"
                      onClick={() =>
                        void openNotification(
                          item,
                        )
                      }
                    >
                      <span
                        className="notification-popover-item-dot"
                        aria-hidden="true"
                      />

                      <span className="notification-popover-item-copy">
                        <span className="notification-popover-item-meta">
                          <b>
                            {categoryLabel(
                              item.category,
                            )}
                          </b>

                          <time>
                            {formatDate(
                              item.created_at,
                            )}
                          </time>
                        </span>

                        <strong>
                          {item.title}
                        </strong>

                        <small>
                          {item.body}
                        </small>
                      </span>
                    </button>

                    <button
                      type="button"
                      className="notification-popover-related"
                      onClick={() =>
                        void openRelatedWork(
                          item,
                        )
                      }
                    >
                      관련 업무
                    </button>
                  </article>
                ),
              )
            )}
          </div>

          <footer className="notification-popover-footer">
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                onOpenCenter();
              }}
            >
              알림센터 전체보기
            </button>
          </footer>
        </section>
      )}
    </div>
  );
}
