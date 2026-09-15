import {
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import AssistantFloatingButton from "./AssistantFloatingButton";
import AssistantFloatingPanel from "./AssistantFloatingPanel";

import type {
  AssistantConversationProps,
} from "./AssistantWorkspace";

import "./assistant.css";


const STORAGE_KEY =
  "brainon-assistant-floating-bottom";

const EDGE_RIGHT = 24;

/*
 * 하단 Action 영역 보호.
 * 진료기록의 임시저장/최종확정 같은
 * 우측 하단 버튼보다 위에 launcher가 위치한다.
 */
const SAFE_BOTTOM = 112;

const TOP_MARGIN = 24;

const BUTTON_SIZE = 76;
const PANEL_GAP = 12;
const PANEL_MIN_HEIGHT = 280;
const PANEL_WIDTH = 380;

const DRAG_THRESHOLD = 5;


interface AssistantFloatingDockProps
  extends AssistantConversationProps {
  isOpen: boolean;

  onToggle: () => void;
  onExpand: () => void;
  onClose: () => void;
}


type DragSource =
  | "button"
  | "panel";


interface DragState {
  source: DragSource;

  startX: number;
  startY: number;

  startRight: number;
  startBottom: number;

  moved: boolean;
}


function getStoredBottom() {
  if (typeof window === "undefined") {
    return SAFE_BOTTOM;
  }

  try {
    const stored =
      window.localStorage.getItem(
        STORAGE_KEY,
      );

    if (!stored) {
      return SAFE_BOTTOM;
    }

    const value = Number(stored);

    if (!Number.isFinite(value)) {
      return SAFE_BOTTOM;
    }

    return Math.max(
      SAFE_BOTTOM,
      value,
    );
  } catch {
    return SAFE_BOTTOM;
  }
}


function saveBottom(
  value: number,
) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      String(value),
    );
  } catch {
    /*
     * localStorage 사용이 제한된 환경에서는
     * 현재 세션 위치만 유지한다.
     */
  }
}


function clampBottom(
  value: number,
  isOpen: boolean,
) {
  if (typeof window === "undefined") {
    return Math.max(
      SAFE_BOTTOM,
      value,
    );
  }

  const reservedHeight =
    BUTTON_SIZE +
    (
      isOpen
        ? PANEL_GAP +
          PANEL_MIN_HEIGHT
        : 0
    );

  const maxBottom = Math.max(
    SAFE_BOTTOM,
    window.innerHeight -
      TOP_MARGIN -
      reservedHeight,
  );

  return Math.min(
    Math.max(
      value,
      SAFE_BOTTOM,
    ),
    maxBottom,
  );
}


function clampRight(
  value: number,
  isOpen: boolean,
) {
  if (typeof window === "undefined") {
    return EDGE_RIGHT;
  }

  const availableWidth =
    Math.max(
      0,
      window.innerWidth - 32,
    );

  const dockWidth =
    isOpen
      ? Math.min(
          PANEL_WIDTH,
          availableWidth,
        )
      : BUTTON_SIZE;

  const maxRight = Math.max(
    EDGE_RIGHT,
    window.innerWidth -
      dockWidth -
      EDGE_RIGHT,
  );

  return Math.min(
    Math.max(
      value,
      EDGE_RIGHT,
    ),
    maxRight,
  );
}


export default function AssistantFloatingDock({
  isOpen,

  onToggle,
  onExpand,
  onClose,

  patientId,

  messages,
  setMessages,

  conversationId,
  setConversationId,
}: AssistantFloatingDockProps) {
  const initialBottom =
    getStoredBottom();

  const [bottom, setBottom] =
    useState(initialBottom);

  const [right, setRight] =
    useState(EDGE_RIGHT);

  const [isDragging, setIsDragging] =
    useState(false);

  const bottomRef =
    useRef(initialBottom);

  const rightRef =
    useRef(EDGE_RIGHT);

  const isOpenRef =
    useRef(isOpen);

  const dragRef =
    useRef<DragState | null>(null);

  const suppressButtonClickRef =
    useRef(false);


  useEffect(() => {
    isOpenRef.current =
      isOpen;
  }, [isOpen]);


  function updateBottom(
    value: number,
  ) {
    bottomRef.current =
      value;

    setBottom(value);
  }


  function updateRight(
    value: number,
  ) {
    rightRef.current =
      value;

    setRight(value);
  }


  function startDrag(
    event: ReactPointerEvent<HTMLElement>,
    source: DragSource,
  ) {
    if (event.button !== 0) {
      return;
    }

    dragRef.current = {
      source,

      startX: event.clientX,
      startY: event.clientY,

      startRight:
        rightRef.current,

      startBottom:
        bottomRef.current,

      moved: false,
    };

    setIsDragging(true);
  }


  /*
   * Drag listener는 한 번만 등록한다.
   * 이동 중 렌더링마다 listener를 다시 붙이지 않는다.
   */
  useEffect(() => {
    function handlePointerMove(
      event: PointerEvent,
    ) {
      const drag =
        dragRef.current;

      if (!drag) {
        return;
      }

      const deltaX =
        event.clientX -
        drag.startX;

      const deltaY =
        event.clientY -
        drag.startY;

      if (
        Math.hypot(
          deltaX,
          deltaY,
        ) >= DRAG_THRESHOLD
      ) {
        drag.moved = true;
      }

      const nextBottom =
        clampBottom(
          drag.startBottom -
            deltaY,
          isOpenRef.current,
        );

      const nextRight =
        clampRight(
          drag.startRight -
            deltaX,
          isOpenRef.current,
        );

      updateBottom(
        nextBottom,
      );

      updateRight(
        nextRight,
      );
    }


    function handlePointerUp() {
      const drag =
        dragRef.current;

      if (!drag) {
        return;
      }

      if (
        drag.source === "button" &&
        drag.moved
      ) {
        suppressButtonClickRef.current =
          true;
      }

      dragRef.current = null;

      setIsDragging(false);

      /*
       * 드래그를 놓으면 항상 우측 가장자리로 스냅.
       */
      updateRight(
        EDGE_RIGHT,
      );

      const nextBottom =
        clampBottom(
          bottomRef.current,
          isOpenRef.current,
        );

      updateBottom(
        nextBottom,
      );

      saveBottom(
        nextBottom,
      );
    }


    window.addEventListener(
      "pointermove",
      handlePointerMove,
    );

    window.addEventListener(
      "pointerup",
      handlePointerUp,
    );

    window.addEventListener(
      "pointercancel",
      handlePointerUp,
    );


    return () => {
      window.removeEventListener(
        "pointermove",
        handlePointerMove,
      );

      window.removeEventListener(
        "pointerup",
        handlePointerUp,
      );

      window.removeEventListener(
        "pointercancel",
        handlePointerUp,
      );
    };
  }, []);


  /*
   * 패널 Open/Close 또는 브라우저 크기 변경 시
   * 화면 밖으로 나가지 않도록 위치를 다시 정규화한다.
   */
  useEffect(() => {
    function normalizePosition() {
      const nextBottom =
        clampBottom(
          bottomRef.current,
          isOpenRef.current,
        );

      updateBottom(
        nextBottom,
      );

      updateRight(
        EDGE_RIGHT,
      );

      saveBottom(
        nextBottom,
      );
    }

    normalizePosition();

    window.addEventListener(
      "resize",
      normalizePosition,
    );

    return () => {
      window.removeEventListener(
        "resize",
        normalizePosition,
      );
    };
  }, [isOpen]);


  function handleButtonClick() {
    if (
      suppressButtonClickRef.current
    ) {
      suppressButtonClickRef.current =
        false;

      return;
    }

    onToggle();
  }


  const dockStyle = {
    right,
    bottom,

    "--assistant-dock-bottom":
      `${bottom}px`,
  } as CSSProperties;


  return (
    <div
      className={
        `assistant-floating-dock${
          isDragging
            ? " is-dragging"
            : ""
        }`
      }
      style={dockStyle}
    >
      {isOpen && (
        <AssistantFloatingPanel
          patientId={patientId}

          messages={messages}
          setMessages={setMessages}

          conversationId={
            conversationId
          }
          setConversationId={
            setConversationId
          }

          onExpand={onExpand}
          onClose={onClose}

          onPointerDragStart={(
            event,
          ) =>
            startDrag(
              event,
              "panel",
            )
          }
        />
      )}

      <AssistantFloatingButton
        onClick={
          handleButtonClick
        }

        onPointerDragStart={(
          event,
        ) =>
          startDrag(
            event,
            "button",
          )
        }
      />
    </div>
  );
}
