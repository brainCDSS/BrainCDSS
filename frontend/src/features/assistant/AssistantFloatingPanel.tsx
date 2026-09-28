import {
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import { sendAssistantMessage } from "./api";

import {
  ASSISTANT_QUICK_PROMPTS,
  type AssistantConversationProps,
} from "./AssistantWorkspace";

import chatAvatar from "./assets/chat-avatar.png";

import "./assistant.css";


/* =========================================================
   Props
   ========================================================= */

interface AssistantFloatingPanelProps
  extends AssistantConversationProps {
  onExpand: () => void;
  onClose: () => void;

  /*
   * FloatingDock이 실제 위치를 관리한다.
   * Panel은 Header에서 Drag 시작 이벤트만 전달한다.
   */
  onPointerDragStart: (
    event: ReactPointerEvent<HTMLElement>,
  ) => void;
}


/* =========================================================
   BrainOn AI Floating Panel
   ========================================================= */

export default function AssistantFloatingPanel({
  patientId,

  onExpand,
  onClose,
  onPointerDragStart,

  messages,
  setMessages,

  conversationId,
  setConversationId,
}: AssistantFloatingPanelProps) {

  const panelRef =
    useRef<HTMLElement>(null);

  const [input, setInput] =
    useState("");

  const [isSending, setIsSending] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);


  /* =======================================================
     패널 외부 클릭 → Floating Panel 닫기
     -------------------------------------------------------
     FloatingDock 내부에서 발생한 클릭은
     외부 클릭으로 취급하지 않는다.
     ======================================================= */

  useEffect(() => {

    function handleOutsideClick(
      event: MouseEvent,
    ) {
      const target =
        event.target;

      if (!(target instanceof Node)) {
        return;
      }

      /*
       * 현재 Panel 내부 클릭
       */
      if (
        panelRef.current?.contains(target)
      ) {
        return;
      }

      /*
       * Floating Button을 포함한
       * 전체 FloatingDock 내부 클릭
       *
       * 기존에는
       * .assistant-floating-button
       * 만 확인했지만,
       *
       * 이제 Button + Panel을
       * 하나의 Dock으로 관리한다.
       */
      if (
        target instanceof Element &&
        target.closest(
          ".assistant-floating-dock",
        )
      ) {
        return;
      }

      onClose();
    }


    document.addEventListener(
      "mousedown",
      handleOutsideClick,
    );


    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick,
      );
    };

  }, [onClose]);


  /* =======================================================
     메시지 전송
     ======================================================= */

  async function handleSend(
    value: string,
  ) {

    const prompt =
      value.trim();

    if (
      !prompt ||
      isSending
    ) {
      return;
    }


    /*
     * 사용자 메시지를 먼저 화면에 표시
     */
    setMessages((previous) => [
      ...previous,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: prompt,
        createdAt:
          new Date().toISOString(),
      },
    ]);


    setInput("");
    setError(null);
    setIsSending(true);


    try {

      const response =
        await sendAssistantMessage({
          message: prompt,

          conversation_id:
            conversationId,

          context: patientId
            ? {
                scope: "PATIENT",
                patient_id: patientId,
                encounter_id: null,
              }
            : {
                scope: "TODAY",
                patient_id: null,
                encounter_id: null,
              },
        });


      /*
       * Conversation 유지
       */
      setConversationId(
        response.conversation_id,
      );


      /*
       * Assistant 응답 추가
       */
      setMessages((previous) => [
        ...previous,
        {
          id: response.message_id,
          role: "assistant",
          content: response.answer,
          createdAt:
            response.created_at,
          actions:
            response.actions,
        },
      ]);

    } catch {

      setError(
        "BrainOn AI 응답을 불러오지 못했습니다.",
      );

    } finally {

      setIsSending(false);

    }

  }


  /* =======================================================
     Form Submit
     ======================================================= */

  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {

    event.preventDefault();

    void handleSend(input);

  }


  /* =======================================================
     Render
     ======================================================= */

  return (
    <section
      ref={panelRef}
      className="assistant-floating-window"
    >

      {/* ===================================================
          Header
          ---------------------------------------------------
          빈 Header 영역을 잡으면 Drag 시작.

          확장 / 닫기 버튼을 클릭한 경우에는
          Drag가 시작되지 않는다.
          =================================================== */}

      <header
        className="assistant-floating-header"

        onPointerDown={(event) => {

          const target =
            event.target;

          /*
           * Header 안의 버튼 클릭은
           * Drag로 처리하지 않는다.
           */
          if (
            target instanceof Element &&
            target.closest("button")
          ) {
            return;
          }

          onPointerDragStart(
            event,
          );

        }}
      >

        <div
          className="assistant-floating-title"
        >
          <strong>
            BrainOn AI
          </strong>

          <span>
            임상 업무 AI 어시스턴트
          </span>
        </div>


        <div
          className="assistant-window-actions"
        >

          <button
            type="button"
            onClick={onExpand}
            aria-label="Workspace로 확장"
            title="확장"
          >
            ↖
          </button>


          <button
            type="button"
            onClick={onClose}
            aria-label="채팅창 닫기"
            title="닫기"
          >
            ×
          </button>

        </div>

      </header>


      {/* ===================================================
          Message Body
          =================================================== */}

      <div
        className="assistant-floating-body"
      >

        {/* 최초 안내 메시지 */}

        {messages.length === 0 && (
          <div
            className="
              assistant-floating-message-row
              assistant-floating-message-row--assistant
            "
          >

            <div
              className="assistant-floating-avatar"
            >
              <img
                src={chatAvatar}
                alt=""
                draggable={false}
                className="assistant-floating-avatar-image"
              />
            </div>


            <div
              className="
                assistant-floating-message
                assistant-floating-message--assistant
              "
            >
              무엇을 도와드릴까요?
            </div>

          </div>
        )}


        {/* Conversation Messages */}

        {messages.map((message) => (

          <div
            key={message.id}

            className={
              `assistant-floating-message-row ` +
              `assistant-floating-message-row--${message.role}`
            }
          >

            {message.role ===
              "assistant" && (

              <div
                className="assistant-floating-avatar"
              >
                <img
                  src={chatAvatar}
                  alt=""
                  draggable={false}
                  className="assistant-floating-avatar-image"
                />
              </div>

            )}


            <div
              className={
                `assistant-floating-message ` +
                `assistant-floating-message--${message.role}`
              }
            >
              {message.content}
            </div>

          </div>

        ))}


        {/* 응답 생성 중 */}

        {isSending && (

          <div
            className="
              assistant-floating-message-row
              assistant-floating-message-row--assistant
            "
          >

            <div
              className="assistant-floating-avatar"
            >
              <img
                src={chatAvatar}
                alt=""
                draggable={false}
                className="assistant-floating-avatar-image"
              />
            </div>


            <div
              className="assistant-floating-typing"
              aria-label="BrainOn AI 응답 생성 중"
            >
              <span />
              <span />
              <span />
            </div>

          </div>

        )}


        {/* API 오류 */}

        {error && (
          <div
            className="assistant-floating-error"
            role="alert"
          >
            {error}
          </div>
        )}

      </div>


      {/* ===================================================
          Composer Area
          =================================================== */}

      <div
        className="assistant-floating-composer-area"
      >

        {/* 빠른 질문 */}

        {messages.length === 0 && (

          <div
            className="assistant-floating-quick"
          >

            <span
              className="assistant-floating-quick-title"
            >
              빠른 질문
            </span>


            {ASSISTANT_QUICK_PROMPTS
              .slice(0, 2)
              .map((prompt) => (

                <button
                  key={prompt}
                  type="button"

                  disabled={
                    isSending
                  }

                  onClick={() =>
                    void handleSend(
                      prompt,
                    )
                  }
                >
                  {prompt}

                  <span>
                    ›
                  </span>
                </button>

              ))}

          </div>

        )}


        {/* 입력창 */}

        <form
          className="assistant-floating-composer"
          onSubmit={handleSubmit}
        >

          <textarea
            rows={1}

            value={input}

            disabled={
              isSending
            }

            placeholder="BrainOn AI에게 질문하세요..."

            aria-label="BrainOn AI 질문 입력"

            onChange={(event) =>
              setInput(
                event.target.value,
              )
            }

            onKeyDown={(event) => {

              /*
               * Enter:
               * 전송
               *
               * Shift + Enter:
               * 줄바꿈
               */
              if (
                event.key === "Enter" &&
                !event.shiftKey
              ) {

                event.preventDefault();

                event.currentTarget.form
                  ?.requestSubmit();

              }

            }}
          />


          <button
            type="submit"

            className="assistant-floating-send"

            disabled={
              !input.trim() ||
              isSending
            }

            aria-label="메시지 전송"
          >
            ↑
          </button>

        </form>

      </div>

    </section>
  );
}