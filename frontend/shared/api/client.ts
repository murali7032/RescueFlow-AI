export type DemoRole = "donor" | "recipient" | "admin";

export interface ApiClientOptions {
  baseUrl?: string;
  role?: DemoRole;
  recipientId?: number | null;
  getToken?: () => string | null;
}

/**
 * Cloud Shell Web Preview cannot call another preview port (e.g. 8000 from 5173):
 * the proxy injects an auth redirect that browsers reject on CORS preflight.
 * Use same-origin requests and let Vite proxy /api → localhost:8000.
 */
function resolveDefaultBase(): string {
  const envUrl =
    typeof import.meta !== "undefined"
      ? (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL
      : undefined;

  if (envUrl === "" || envUrl === "/") {
    return "";
  }

  if (
    typeof window !== "undefined" &&
    /\.cloudshell\.dev$/i.test(window.location.hostname)
  ) {
    return "";
  }

  if (envUrl && envUrl.trim()) {
    return envUrl.replace(/\/$/, "");
  }

  return "http://localhost:8000";
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export function createApiClient(options: ApiClientOptions = {}) {
  const baseUrl = options.baseUrl ?? resolveDefaultBase();

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string> | undefined),
    };

    const token = options.getToken?.();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    } else {
      headers["X-Demo-Role"] = options.role ?? "admin";
      headers["X-Demo-User-Id"] = `demo-${options.role ?? "admin"}`;
      if (options.recipientId != null) {
        headers["X-Demo-Recipient-Id"] = String(options.recipientId);
      }
    }

    const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
    const text = await response.text();
    let body: unknown = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = text;
      }
    }
    if (!response.ok) {
      const detail =
        typeof body === "object" && body && "detail" in body
          ? String((body as { detail: unknown }).detail)
          : response.statusText;
      throw new ApiError(response.status, detail, body);
    }
    return body as T;
  }

  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body?: unknown) =>
      request<T>(path, {
        method: "POST",
        body: body === undefined ? undefined : JSON.stringify(body),
      }),
    patch: <T>(path: string, body?: unknown) =>
      request<T>(path, {
        method: "PATCH",
        body: body === undefined ? undefined : JSON.stringify(body),
      }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
