"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

export interface Toast {
  id: number;
  kind: "success" | "error" | "info";
  title: string;
  message?: string;
}

const ToastContext = createContext<{ notify: (t: Omit<Toast, "id">) => void }>({ notify: () => undefined });

let nextId = 1;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const notify = useCallback((t: Omit<Toast, "id">) => {
    const id = nextId++;
    setToasts((prev) => [...prev, { ...t, id }]);
    window.setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 6000);
  }, []);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>
            <button className="toast-close" onClick={() => dismiss(t.id)} aria-label="Dismiss notification">
              ×
            </button>
            <strong>{t.title}</strong>
            {t.message ? <span>{t.message}</span> : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): (t: Omit<Toast, "id">) => void {
  return useContext(ToastContext).notify;
}
