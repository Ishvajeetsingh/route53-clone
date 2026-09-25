"use client";

import { useEffect, useRef, useState } from "react";
import { RECORD_TYPES, ROUTING_POLICIES } from "@/types";
import { hintFor, placeholderFor } from "@/lib/format";

export interface RecordFormValues {
  name: string;
  type: string;
  values: string[];
  ttl: number;
  routing_policy: string;
  description: string;
}

export default function RecordModal({
  title,
  zoneName,
  initial,
  busy,
  error,
  systemNotice = null,
  onClose,
  onSubmit,
}: {
  title: string;
  zoneName: string;
  initial: RecordFormValues;
  busy: boolean;
  error: string | null;
  systemNotice?: string | null;
  onClose: () => void;
  onSubmit: (values: RecordFormValues) => void;
}) {
  const isEdit = title.toLowerCase().includes("edit");
  const [name, setName] = useState(initial.name);
  const [type, setType] = useState(initial.type);
  const [valuesText, setValuesText] = useState(initial.values.join("\n"));
  const [ttl, setTtl] = useState(String(initial.ttl));
  const [policy, setPolicy] = useState(initial.routing_policy);
  const [description, setDescription] = useState(initial.description);
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
    const values = valuesText.split("\n").map((v) => v.trim()).filter(Boolean);
    if (!name.trim()) {
      setLocalError("Record name is required.");
      return;
    }
    if (values.length === 0) {
      setLocalError("Enter at least one value.");
      return;
    }
    if (type === "CNAME" && values.length !== 1) {
      setLocalError("CNAME records must have exactly one value.");
      return;
    }
    const ttlNum = Number(ttl);
    if (!Number.isInteger(ttlNum) || ttlNum < 1 || ttlNum > 2147483647) {
      setLocalError("TTL must be an integer between 1 and 2147483647 seconds.");
      return;
    }
    setLocalError(null);
    onSubmit({ name: name.trim(), type, values, ttl: ttlNum, routing_policy: policy, description: description.trim() });
  }

  return (
    <div className="modal-backdrop" onClick={() => { if (!busy) onClose(); }}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-header">{title}</div>
        <form onSubmit={submit}>
          <div className="modal-body">
            {error ? <div className="alert alert-error" role="alert">{error}</div> : null}
            {localError ? <div className="alert alert-error" role="alert">{localError}</div> : null}
            {systemNotice ? <div className="alert alert-info">{systemNotice}</div> : null}
            <div className="alert alert-info">
              {isEdit ? (
                <>Editing record in <strong>{zoneName}</strong>. Record type cannot be changed.</>
              ) : (
                <>Creating records in <strong>{zoneName}</strong>. Record names are stored as fully qualified domain names.</>
              )}
            </div>
            <div className="form-grid">
              <label htmlFor="rec-name">
                Record name <span className="req">*</span>
              </label>
              <div className="field">
                <input ref={firstFieldRef} id="rec-name" type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={`www.${zoneName}`} disabled={busy} />
              </div>
              <label htmlFor="rec-type">Record type</label>
              <div className="field">
                <select id="rec-type" value={type} onChange={(e) => setType(e.target.value)} disabled={busy || isEdit}>
                  {RECORD_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                {isEdit ? <div className="hint">Record type cannot be changed after creation.</div> : null}
              </div>
              <label htmlFor="rec-values">
                Value(s) <span className="req">*</span>
              </label>
              <div className="field">
                <textarea
                  id="rec-values"
                  value={valuesText}
                  onChange={(e) => setValuesText(e.target.value)}
                  placeholder={placeholderFor(type)}
                  disabled={busy}
                />
                <div className="hint">{hintFor(type)} Put each value on its own line.</div>
              </div>
              <label htmlFor="rec-ttl">TTL (seconds)</label>
              <div className="field">
                <input id="rec-ttl" type="number" min={1} max={2147483647} value={ttl} onChange={(e) => setTtl(e.target.value)} disabled={busy} />
                <div className="hint">Common values: 60, 300, 3600, 86400.</div>
              </div>
              <label htmlFor="rec-policy">Routing policy</label>
              <div className="field">
                <select id="rec-policy" value={policy} onChange={(e) => setPolicy(e.target.value)} disabled={busy}>
                  {ROUTING_POLICIES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <label htmlFor="rec-desc">Description</label>
              <div className="field">
                <input id="rec-desc" type="text" value={description} onChange={(e) => setDescription(e.target.value)} disabled={busy} maxLength={1024} />
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
                "Save record"
              ) : (
                "Create record"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
