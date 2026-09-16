import type {
  PointerEvent as ReactPointerEvent,
} from "react";

import floatingImage from "./assets/floating.png";

import "./assistant.css";


interface AssistantFloatingButtonProps {
  onClick: () => void;

  onPointerDragStart: (
    event: ReactPointerEvent<HTMLButtonElement>,
  ) => void;
}


export default function AssistantFloatingButton({
  onClick,
  onPointerDragStart,
}: AssistantFloatingButtonProps) {
  return (
    <button
      type="button"
      className="assistant-floating-launcher"
      onPointerDown={onPointerDragStart}
      onClick={onClick}
      aria-label="BrainOn AI 열기 또는 닫기"
      title="BrainOn AI"
    >
      <img
        src={floatingImage}
        alt="BrainOn AI"
        draggable={false}
        className="assistant-floating-button-image"
      />
    </button>
  );
}
