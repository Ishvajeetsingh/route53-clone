"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { username, ready, signIn } = useAuth();
  const router = useRouter();
  const [formUser, setFormUser] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const userRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (ready && username) router.replace("/dashboard");
  }, [ready, username, router]);

  useEffect(() => {
    userRef.current?.focus();
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!formUser.trim()) {
      setError("Enter a username to sign in.");
      return;
    }
    if (!password) {
      setError("Enter a password to sign in.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn(formUser.trim(), password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed. Check that the API is reachable and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="brand-bar">
          <strong>aws</strong> <span style={{ color: "#ff9900" }}>&#63743;</span> &nbsp;Route 53 Management Console
        </div>
        <form className="login-body" onSubmit={submit} autoComplete="off">
          <h1 style={{ fontSize: 20, margin: "0 0 4px" }}>Sign in</h1>
          <p style={{ color: "#5f6b6a", fontSize: 13, margin: "0 0 16px" }}>
            This demo console is not operated by AWS. Sign-in is mocked — any username and password will work, so
            don&apos;t enter real credentials.
          </p>
          {error ? (
            <div className="alert alert-error" role="alert">
              {error}
            </div>
          ) : null}
          <div className="form-grid" style={{ gridTemplateColumns: "130px 1fr" }}>
            <label htmlFor="login-user">Username</label>
            <div className="field">
              <input
                ref={userRef}
                id="login-user"
                type="text"
                value={formUser}
                onChange={(e) => setFormUser(e.target.value)}
                autoComplete="off"
                placeholder="e.g. admin"
                disabled={busy}
              />
            </div>
            <label htmlFor="login-pass">Password</label>
            <div className="field">
              <input
                id="login-pass"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="off"
                placeholder="••••••••"
                disabled={busy}
              />
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? (
                <>
                  <span className="spinner" /> Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
