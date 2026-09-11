import {
  useEffect,
  useRef,
} from "react";

import "./assistant.css";

interface AssistantFloatingPanelProps {
  onExpand: () => void;
  onClose: () => void;
}

export default function AssistantFloatingPanel({
  onExpand,
  onClose,
}: AssistantFloatingPanelProps) {
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const handleOutsideClick = (
      event: MouseEvent,
    ) => {
      const target = event.target;

      if (!(target instanceof Node)) {
        return;
      }

      // 채팅창 내부 클릭
      if (
        panelRef.current &&
        panelRef.current.contains(target)
      ) {
        return;
      }

      // AI 플로팅 버튼 클릭은 바깥 클릭으로 처리하지 않음
      if (
        target instanceof Element &&
        target.closest(
          ".assistant-floating-button",
        )
      ) {
        return;
      }

      // 그 외 화면 클릭
      onClose();
    };

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

  return (
    <section
      ref={panelRef}
      className="assistant-floating-panel"
    >
      <header className="assistant-floating-header">
        <div className="assistant-floating-title">
          <strong>BrainOn AI</strong>

          <span>
            임상 의사결정 지원
          </span>
        </div>

        <div className="assistant-window-actions">
          {/* Workspace 확장 */}
          <button
            type="button"
            onClick={onExpand}
            aria-label="워크스페이스로 확장"
            title="확장"
          >
            ↖
          </button>

          {/* 닫기 */}
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

      <div className="assistant-floating-body">
        {/* 다음 단계에서 채팅 UI 추가 */}
      </div>
    </section>
  );
}