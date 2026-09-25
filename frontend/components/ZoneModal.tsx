"use client";

import { useEffect, useRef, useState } from "react";

export default function ZoneModal({
  title,
  initial,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  title: string;
  initial: { name: string; description: string; type: string };
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (values: { name?: string; description: string; type: "Public" | "Private" }) => void;
}) {
  const isEdit = initial.name !== "";
  const [name, setName] = useState(initial.name);
  const [description, setDescription] = useState(initial.description);
  const [type, setType] = useState(initial.type);
  const [localError, setLocalError] = useState<string | null>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstFieldRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onClose]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!isEdit && name.trim().length < 3) {
      setLocalError("Enter a valid domain name (e.g. example.com).");
      return;
    }
    setLocalError(null);
    onSubmit({
      ...(isEdit ? {} : { name: name.trim() }),
      description: description.trim(),
      type: (type === "Private" ? "Private" : "Public") as "Public" | "Private",
    });
  }

  return (
    <div className="modal-backdrop" onClick={() => { if (!busy) onClose(); }}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-header">{title}</div>
        <form onSubmit={submit}>
          <div className="modal-body">
            {error ? <div className="alert alert-error" role="alert">{error}</div> : null}
            {localError ? <div className="alert alert-error" role="alert">{localError}</div> : null}
            <div className="form-grid">
              <label htmlFor="zone-name">
                Domain name <span className="req">*</span>
              </label>
              <div className="field">
                <input
                  ref={firstFieldRef}
                  id="zone-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="example.com"
                  disabled={isEdit || busy}
                />
                <div className="hint">
                  {isEdit ? "Domain name cannot be changed after creation." : "Apex domain for the hosted zone, e.g. example.com."}
                </div>
              </div>
              <label htmlFor="zone-desc">Comment</label>
              <div className="field">
                <input
                  id="zone-desc"
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Production website zone"
                  disabled={busy}
                  maxLength={1024}
                />
              </div>
              <label htmlFor="zone-type">Type</label>
              <div className="field">
                <select id="zone-type" value={type} onChange={(e) => setType(e.target.value)} disabled={busy}>
                  <option value="Public">Public hosted zone</option>
                  <option value="Private">Private hosted zone</option>
                </select>
                <div className="hint">Private zones are associated with a VPC in real Route 53; modelled here as a label.</div>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? (
                <>
                  <span className="spinner" /> Saving…
                </>
              ) : isEdit ? (
                "Save changes"
              ) : (
                "Create hosted zone"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
