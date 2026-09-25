export const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const TOKEN_KEY = "r53_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setSession(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearSession(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg ?? "Validation error").join("; ");
    }
    return `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options.headers) {
    for (const [k, v] of Object.entries(options.headers as Record<string, string>)) headers[k] = v;
  }
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 204) return undefined as unknown as T;
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return (await res.json()) as T;
}

export async function login(username: string, password: string): Promise<{ token: string; user: { username: string } }> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return (await res.json()) as { token: string; user: { username: string } };
}

export async function logoutRemote(): Promise<void> {
  const token = getToken();
  try {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    // logout is best-effort; local session is cleared regardless
  }
}
