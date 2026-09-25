"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, clearSession, getToken, login, logoutRemote, setSession } from "@/lib/api";

interface AuthState {
  username: string | null;
  ready: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  username: null,
  ready: false,
  signIn: async () => undefined,
  signOut: async () => undefined,
});

// Bound the startup session check: a hanging backend must resolve to the
// login screen, never to a permanent loading state.
const BOOT_TIMEOUT_MS = 10000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("Session check timed out")), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      const token = getToken();
      if (!token) {
        if (!cancelled) {
          setUsername(null);
          setReady(true);
        }
        return;
      }
      try {
        const me = await withTimeout(api<{ user: { username: string } }>("/api/auth/me"), BOOT_TIMEOUT_MS);
        if (!cancelled) setUsername(me.user.username);
      } catch {
        clearSession();
        if (!cancelled) setUsername(null);
      } finally {
        if (!cancelled) setReady(true);
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (u: string, p: string) => {
    const res = await login(u, p);
    setSession(res.token);
    setUsername(res.user.username);
  }, []);

  const signOut = useCallback(async () => {
    await logoutRemote();
    clearSession();
    setUsername(null);
    router.push("/login");
  }, [router]);

  const value = useMemo(() => ({ username, ready, signIn, signOut }), [username, ready, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
