"use client";

import { useEffect, useRef } from "react";

export default function ConfirmModal({
  title,
  body,
  confirmLabel = "Delete",
  busy = false,
  onCancel,
  onConfirm,
}: {
  title: string;
  body: React.ReactNode;
  confirmLabel?: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    cancelRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onCancel]);

  return (
    <div className="modal-backdrop" onClick={() => { if (!busy) onCancel(); }}>
      <div
        className="modal narrow"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="modal-header">{title}</div>
        <div className="modal-body">{body}</div>
        <div className="modal-footer">
          <button ref={cancelRef} className="btn" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="btn btn-danger" onClick={onConfirm} disabled={busy}>
            {busy ? (
              <>
                <span className="spinner" aria-hidden="true" /> Working…
              </>
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
