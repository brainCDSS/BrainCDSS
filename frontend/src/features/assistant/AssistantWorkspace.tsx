import {
  type FormEvent,
  useState,
} from "react";

import "./assistant.css";

type ChatRole = "assistant" | "user";

interface ChatMessage {
  id: number;
  role: ChatRole;
  content: string;
  time: string;
  actions?: string[];
}

const QUICK_PROMPTS = [
  "오늘 예약 환자 현황 알려줘",
  "현재 대기 환자 알려줘",
  "오늘 영상검사 예정 환자 알려줘",
  "새 협진 요청 요약해줘",
];

function getCurrentTime() {
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date());
}

function getMockResponse(prompt: string): ChatMessage {
  const time = getCurrentTime();

  if (prompt.includes("예약")) {
    return {
      id: Date.now() + 1,
      role: "assistant",
      content:
        "네, 오늘 예약된 환자 현황을 확인했습니다.\n\n총 8명의 환자가 예약되어 있으며, 오전 5명 · 오후 3명입니다.\n이 중 1명은 긴급 환자로 표시되어 있습니다.\n\n더 자세한 목록이 필요하시면 확인해 드릴까요?",
      time,
      actions: [
        "예약 환자 목록 보기",
        "시간대별 현황 보기",
      ],
    };
  }

  if (prompt.includes("대기")) {
    return {
      id: Date.now() + 1,
      role: "assistant",
      content:
        "현재 대기 중인 환자는 총 4명입니다.\n\n초기평가 대기 2명, 영상검사 대기 1명, 진료 대기 1명입니다.",
      time,
      actions: [
        "대기 환자 목록 보기",
      ],
    };
  }

  if (
    prompt.includes("영상") ||
    prompt.includes("검사")
  ) {
    return {
      id: Date.now() + 1,
      role: "assistant",
      content:
        "오늘 예정된 영상검사는 총 6건입니다.\n\nCT 3건, MRI 2건, MRA 1건이 예정되어 있습니다.",
      time,
      actions: [
        "영상검사 일정 보기",
      ],
    };
  }

  if (prompt.includes("협진")) {
    return {
      id: Date.now() + 1,
      role: "assistant",
      content:
        "현재 확인이 필요한 신규 협진 요청은 2건입니다.\n\n우선순위와 요청 내용을 기준으로 정리해서 확인할 수 있습니다.",
      time,
      actions: [
        "협진 요청 목록 보기",
      ],
    };
  }

  return {
    id: Date.now() + 1,
    role: "assistant",
    content:
      "요청을 확인했습니다.\n실제 임상 데이터 조회는 Backend Assistant API 연결 후 제공될 예정입니다.",
    time,
  };
}

export default function AssistantWorkspace() {
  const [input, setInput] = useState("");

  const [
    messages,
    setMessages,
  ] = useState<ChatMessage[]>([]);

  const [
    isResponding,
    setIsResponding,
  ] = useState(false);

  const handleSend = (
    value: string,
  ) => {
    const prompt = value.trim();

    if (!prompt || isResponding) {
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now(),
      role: "user",
      content: prompt,
      time: getCurrentTime(),
    };

    setMessages((previous) => [
      ...previous,
      userMessage,
    ]);

    setInput("");
    setIsResponding(true);

    window.setTimeout(() => {
      setMessages((previous) => [
        ...previous,
        getMockResponse(prompt),
      ]);

      setIsResponding(false);
    }, 500);
  };

  const handleSubmit = (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();
    handleSend(input);
  };

  return (
    <section className="assistant-workspace">
      {/* ================================
          Header
          ================================ */}

      <header className="assistant-workspace-header">
        <div className="assistant-workspace-brand">
          <div className="assistant-workspace-logo">
            AI
          </div>

          <div>
            <h2>BrainOn AI</h2>

            <p>
              임상 업무 조회 · 요약 · 의사결정을
              지원하는 AI 어시스턴트입니다.
            </p>
          </div>
        </div>

        <div className="assistant-workspace-status">
          <span className="assistant-status-dot" />
          사용 가능
        </div>
      </header>

      {/* ================================
          Chat Card
          ================================ */}

      <div className="assistant-workspace-content">
        <div className="assistant-chat-card">
          {/* Context */}

          <div className="assistant-context-bar">
            <div className="assistant-context-info">
              <span className="assistant-context-icon">
                ▣
              </span>

              <strong>현재 컨텍스트</strong>

              <span className="assistant-context-divider">
                |
              </span>

              <span>
                전체 업무 · 오늘
              </span>
            </div>

            <button
              type="button"
              className="assistant-context-button"
            >
              ⚙
              <span>컨텍스트 변경</span>
              <span>⌄</span>
            </button>
          </div>

          {/* Messages */}

          <div className="assistant-chat-scroll">
            {/* 첫 AI 안내 메시지 */}

            <div className="assistant-message-row assistant-message-row--assistant">
              <div className="assistant-message-avatar">
                AI
              </div>

              <div className="assistant-message-group">
                <div className="assistant-message assistant-message--assistant">
                  안녕하세요. 오늘 어떤 업무를
                  도와드릴까요?
                  <br />
                  예약, 환자, 검사, 협진 현황을
                  조회하고 요약할 수 있습니다.
                </div>
              </div>
            </div>

            {/* 빠른 질문 */}

            <div className="assistant-quick-area">
              <div className="assistant-quick-title">
                <span>ϟ</span>
                빠른 질문
              </div>

              <div className="assistant-quick-grid">
                {QUICK_PROMPTS.map(
                  (prompt, index) => (
                    <button
                      key={prompt}
                      type="button"
                      className="assistant-quick-prompt"
                      onClick={() => {
                        handleSend(prompt);
                      }}
                    >
                      <span className="assistant-quick-icon">
                        {index === 0
                          ? "□"
                          : index === 1
                            ? "♙"
                            : index === 2
                              ? "▤"
                              : "▣"}
                      </span>

                      <span>
                        {prompt}
                      </span>

                      <span className="assistant-quick-arrow">
                        ›
                      </span>
                    </button>
                  ),
                )}
              </div>
            </div>

            {/* 실제 대화 */}

            {messages.map((message) => (
              <div
                key={message.id}
                className={
                  message.role === "user"
                    ? "assistant-message-row assistant-message-row--user"
                    : "assistant-message-row assistant-message-row--assistant"
                }
              >
                {message.role === "assistant" && (
                  <div className="assistant-message-avatar">
                    AI
                  </div>
                )}

                <div className="assistant-message-group">
                  <div
                    className={
                      message.role === "user"
                        ? "assistant-message assistant-message--user"
                        : "assistant-message assistant-message--assistant"
                    }
                  >
                    {message.content
                      .split("\n")
                      .map((line, index) => (
                        <span
                          key={`${message.id}-${index}`}
                        >
                          {line}

                          {index <
                            message.content
                              .split("\n")
                              .length -
                              1 && <br />}
                        </span>
                      ))}
                  </div>

                  <span className="assistant-message-time">
                    {message.time}
                  </span>

                  {message.actions &&
                    message.actions.length > 0 && (
                      <div className="assistant-message-actions">
                        {message.actions.map(
                          (action) => (
                            <button
                              key={action}
                              type="button"
                            >
                              {action}
                            </button>
                          ),
                        )}
                      </div>
                    )}
                </div>

                {message.role === "user" && (
                  <div className="assistant-user-avatar">
                    ♙
                  </div>
                )}
              </div>
            ))}

            {isResponding && (
              <div className="assistant-message-row assistant-message-row--assistant">
                <div className="assistant-message-avatar">
                  AI
                </div>

                <div className="assistant-typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
          </div>

          {/* ================================
              Input
              ================================ */}

          <div className="assistant-composer-area">
            <form
              className="assistant-composer"
              onSubmit={handleSubmit}
            >
              <button
                type="button"
                className="assistant-attach-button"
                aria-label="파일 첨부"
                title="파일 첨부"
              >
                ⌕
              </button>

              <textarea
                value={input}
                rows={1}
                placeholder="BrainOn AI에게 질문하세요..."
                aria-label="BrainOn AI 질문 입력"
                onChange={(event) => {
                  setInput(event.target.value);
                }}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey
                  ) {
                    event.preventDefault();

                    event.currentTarget.form?.requestSubmit();
                  }
                }}
              />

              <button
                type="submit"
                className="assistant-send-button"
                disabled={
                  !input.trim() ||
                  isResponding
                }
                aria-label="메시지 전송"
              >
                ↑
              </button>
            </form>

            <div className="assistant-composer-help">
              Enter 전송 · Shift+Enter 줄바꿈
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}