import { useState } from "react";

interface ConsultationReasonModalProps {
  title: string;
  description: string;
  placeholder: string;
  confirmLabel: string;
  busy?: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}

export default function ConsultationReasonModal({
  title,
  description,
  placeholder,
  confirmLabel,
  busy = false,
  onClose,
  onConfirm,
}: ConsultationReasonModalProps) {
  const [reason, setReason] = useState("");
  const trimmedReason = reason.trim();

  return (
    <div
      className="consultation-reason-modal__backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <section
        className="consultation-reason-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="consultation-reason-modal-title"
      >
        <header className="consultation-reason-modal__header">
          <div>
            <h2 id="consultation-reason-modal-title">{title}</h2>
            <p>{description}</p>
          </div>
          <button
            type="button"
            className="consultation-reason-modal__close"
            aria-label={`${title} 닫기`}
            disabled={busy}
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <label className="consultation-reason-modal__field">
          <span>사유 *</span>
          <textarea
            autoFocus
            value={reason}
            disabled={busy}
            placeholder={placeholder}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>

        <footer className="consultation-reason-modal__actions">
          <button type="button" disabled={busy} onClick={onClose}>
            닫기
          </button>
          <button
            type="button"
            className="consultation-reason-modal__confirm"
            disabled={busy || !trimmedReason}
            onClick={() => onConfirm(trimmedReason)}
          >
            {busy ? "처리 중..." : confirmLabel}
          </button>
        </footer>
      </section>
    </div>
  );
}
