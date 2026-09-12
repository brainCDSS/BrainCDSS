import "./assistant.css";
import floatingImage from "./assets/floating.png";

interface AssistantFloatingButtonProps {
  onClick: () => void;
}

export default function AssistantFloatingButton({
  onClick,
}: AssistantFloatingButtonProps) {
  return (
    <button
      type="button"
      className="assistant-floating-button"
      onMouseDown={(event) => {
        event.preventDefault();
        event.stopPropagation();

        onClick();
      }}
      aria-label="BrainOn AI 열기 또는 닫기"
      title="BrainOn AI"
    >
      <img
        src={floatingImage}
        alt="BrainOn AI"
        className="assistant-floating-button-image"
      />
    </button>
  );
}