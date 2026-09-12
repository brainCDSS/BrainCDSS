import { type FormEvent, useEffect, useRef, useState } from "react";

import { sendAssistantMessage } from "./api";
import {
  ASSISTANT_QUICK_PROMPTS,
  type AssistantConversationProps,
} from "./AssistantWorkspace";
import "./assistant.css";

interface AssistantFloatingPanelProps extends AssistantConversationProps {
  onExpand: () => void;
  onClose: () => void;
}

export default function AssistantFloatingPanel({
  onExpand,
  onClose,
  messages,
  setMessages,
  conversationId,
  setConversationId,
}: AssistantFloatingPanelProps) {
  const panelRef = useRef<HTMLElement>(null);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (panelRef.current?.contains(target)) return;
      if (target instanceof Element && target.closest(".assistant-floating-button")) return;
      onClose();
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [onClose]);

  async function handleSend(value: string) {
    const prompt = value.trim();
    if (!prompt || isSending) return;

    setMessages((previous) => [...previous, {
      id: `user-${Date.now()}`,
      role: "user",
      content: prompt,
      createdAt: new Date().toISOString(),
    }]);
    setInput("");
    setError(null);
    setIsSending(true);

    try {
      const response = await sendAssistantMessage({
        message: prompt,
        conversation_id: conversationId,
        context: { scope: "TODAY", patient_id: null, encounter_id: null },
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
      setError("BrainOn AI 응답을 불러오지 못했습니다.");
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void handleSend(input);
  }

  return (
    <section ref={panelRef} className="assistant-floating-panel">
      <header className="assistant-floating-header">
        <div className="assistant-floating-title"><strong>BrainOn AI</strong><span>임상 업무 AI 어시스턴트</span></div>
        <div className="assistant-window-actions">
          <button type="button" onClick={onExpand} aria-label="Workspace로 확장" title="확장">↖</button>
          <button type="button" onClick={onClose} aria-label="채팅창 닫기" title="닫기">×</button>
        </div>
      </header>

      <div className="assistant-floating-body">
        {messages.length === 0 && <div className="assistant-floating-message-row assistant-floating-message-row--assistant">
          <div className="assistant-floating-avatar">AI</div>
          <div className="assistant-floating-message assistant-floating-message--assistant">필요한 임상 업무를 질문해 주세요.</div>
        </div>}

        {messages.map((message) => <div key={message.id} className={`assistant-floating-message-row assistant-floating-message-row--${message.role}`}>
          {message.role === "assistant" && <div className="assistant-floating-avatar">AI</div>}
          <div className={`assistant-floating-message assistant-floating-message--${message.role}`}>{message.content}</div>
        </div>)}

        {isSending && <div className="assistant-floating-message-row assistant-floating-message-row--assistant"><div className="assistant-floating-avatar">AI</div><div className="assistant-floating-typing"><span /><span /><span /></div></div>}
        {error && <div className="assistant-floating-error">{error}</div>}
      </div>

      <div className="assistant-floating-composer-area">
        {messages.length === 0 && <div className="assistant-floating-quick">
          <span className="assistant-floating-quick-title">빠른 질문</span>
          {ASSISTANT_QUICK_PROMPTS.slice(0, 2).map((prompt) => <button key={prompt} type="button" disabled={isSending} onClick={() => void handleSend(prompt)}>{prompt}<span>›</span></button>)}
        </div>}
        <form className="assistant-floating-composer" onSubmit={handleSubmit}>
          <textarea rows={1} value={input} disabled={isSending} placeholder="BrainOn AI에게 질문하세요..." aria-label="BrainOn AI 질문 입력" onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }} />
          <button type="submit" className="assistant-floating-send" disabled={!input.trim() || isSending} aria-label="메시지 전송">↑</button>
        </form>
      </div>
    </section>
  );
}
