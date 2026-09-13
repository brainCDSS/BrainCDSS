import { type Dispatch, type FormEvent, type SetStateAction, useState } from "react";

import { sendAssistantMessage } from "./api";
import type { AssistantAction, AssistantChatMessage } from "./types";
import "./assistant.css";

export const ASSISTANT_QUICK_PROMPTS = [
  "오늘 예약 환자 현황 알려줘",
  "현재 대기 환자 알려줘",
  "오늘 영상검사 예정 환자 알려줘",
  "신규 협진 요청 요약해줘",
];

export interface AssistantConversationProps {
  patientId: string | null;
  messages: AssistantChatMessage[];
  setMessages: Dispatch<SetStateAction<AssistantChatMessage[]>>;
  conversationId: string | null;
  setConversationId: Dispatch<SetStateAction<string | null>>;
}

interface AssistantWorkspaceProps extends AssistantConversationProps {
  onMinimize: () => void;
  onClose: () => void;
}

function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : new Intl.DateTimeFormat("ko-KR", { hour: "numeric", minute: "2-digit" }).format(date);
}

export default function AssistantWorkspace({
  patientId,
  messages,
  setMessages,
  conversationId,
  setConversationId,
  onMinimize,
  onClose,
}: AssistantWorkspaceProps) {
  const [input, setInput] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [showNewConversationConfirm, setShowNewConversationConfirm] = useState(false);

  function resetConversation() {
    setMessages([]);
    setConversationId(null);
    setInput("");
    setRequestError(null);
    setShowNewConversationConfirm(false);
  }

  function handleNewConversation() {
    if (messages.length > 0) {
      setShowNewConversationConfirm(true);
      return;
    }
    resetConversation();
  }

  async function handleSend(value: string) {
    const prompt = value.trim();
    if (!prompt || isPending) return;

    setMessages((previous) => [...previous, {
      id: `user-${Date.now()}`,
      role: "user",
      content: prompt,
      createdAt: new Date().toISOString(),
    }]);
    setInput("");
    setRequestError(null);
    setIsPending(true);

    try {
      const response = await sendAssistantMessage({
        message: prompt,
        conversation_id: conversationId,
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
      setConversationId(response.conversation_id);
      setMessages((previous) => [...previous, {
        id: response.message_id,
        role: "assistant",
        content: response.answer,
        createdAt: response.created_at,
        actions: response.actions,
      }]);
    } catch {
      setRequestError("BrainOn AI 응답을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setIsPending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void handleSend(input);
  }

  function renderActions(actions: AssistantAction[]) {
    return <div className="assistant-message-actions">{actions.map((action) => (
      <button key={`${action.type}-${action.target_id ?? ""}-${action.label}`} type="button">
        {action.label}
      </button>
    ))}</div>;
  }

  return (
    <section className="assistant-workspace">
      <header className="assistant-workspace-header">
        <div className="assistant-workspace-brand">
          <div className="assistant-workspace-logo">AI</div>
          <div>
            <h2>BrainOn AI</h2>
            <p>임상 업무 조회와 요약을 지원하는 AI 어시스턴트입니다.</p>
          </div>
        </div>
        <div className="assistant-workspace-actions">
          <button type="button" disabled={isPending} onClick={handleNewConversation} aria-label="새 대화 시작" title="새 대화">＋</button>
          <button type="button" onClick={onMinimize} aria-label="플로팅 Assistant로 축소" title="축소">↘</button>
          <button type="button" onClick={onClose} aria-label="BrainOn AI Workspace 닫기" title="닫기">×</button>
        </div>
      </header>

      <div className="assistant-workspace-content">
        <div className="assistant-chat-card">
          <div className="assistant-chat-scroll">
            {messages.length === 0 && <div className="assistant-message-row assistant-message-row--assistant assistant-intro-message">
              <div className="assistant-message-avatar">AI</div>
              <div className="assistant-message-group">
                <div className="assistant-message assistant-message--assistant">
                  <strong>필요한 임상 업무를 질문해 주세요.</strong>
                  <span>진료, 영상, 리포트 등 다양한 업무를 도와드립니다.</span>
                </div>
              </div>
            </div>}

            {messages.map((message) => <div key={message.id} className={`assistant-message-row assistant-message-row--${message.role}`}>
              {message.role === "assistant" && <div className="assistant-message-avatar">AI</div>}
              <div className="assistant-message-group">
                <div className={`assistant-message assistant-message--${message.role}`}>{message.content}</div>
                <span className="assistant-message-time">{formatTime(message.createdAt)}</span>
                {message.actions?.length ? renderActions(message.actions) : null}
              </div>
            </div>)}

            {isPending && <div className="assistant-message-row assistant-message-row--assistant">
              <div className="assistant-message-avatar">AI</div>
              <div className="assistant-typing" aria-label="응답 대기 중"><span /><span /><span /></div>
            </div>}
            {requestError && <div className="assistant-request-error" role="alert">{requestError}</div>}
          </div>

          <div className="assistant-workspace-bottom">
            <div className="assistant-quick-area">
              <div className="assistant-quick-title">빠른 질문</div>
              <div className="assistant-quick-grid">{ASSISTANT_QUICK_PROMPTS.map((prompt) => (
                <button key={prompt} type="button" className="assistant-quick-prompt" disabled={isPending} onClick={() => void handleSend(prompt)}>
                  <span>{prompt}</span><span className="assistant-quick-arrow">›</span>
                </button>
              ))}</div>
            </div>

            <div className="assistant-composer-area">
              <form className="assistant-composer" onSubmit={handleSubmit}>
                <button type="button" className="assistant-attach-button" aria-label="파일 첨부" title="파일 첨부">＋</button>
                <textarea value={input} rows={1} placeholder="BrainOn AI에게 질문하세요..." aria-label="BrainOn AI 질문 입력" disabled={isPending} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }} />
                <button type="submit" className="assistant-send-button" disabled={!input.trim() || isPending} aria-label="메시지 전송">↑</button>
              </form>
              <div className="assistant-composer-help">Enter 전송 · Shift+Enter 줄바꿈</div>
            </div>
          </div>
        </div>
      </div>

      {showNewConversationConfirm && <div className="assistant-confirm-layer" role="presentation" onMouseDown={() => setShowNewConversationConfirm(false)}>
        <section className="assistant-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="assistant-new-conversation-title" onMouseDown={(event) => event.stopPropagation()}>
          <h3 id="assistant-new-conversation-title">새 대화를 시작할까요?</h3>
          <p>현재 대화가 초기화됩니다.</p>
          <div><button type="button" onClick={() => setShowNewConversationConfirm(false)}>취소</button><button type="button" className="is-primary" onClick={resetConversation}>새 대화</button></div>
        </section>
      </div>}
    </section>
  );
}
