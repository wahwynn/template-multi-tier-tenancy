import type { ApiErrorBody } from "@/types/api";

interface ClientConfig {
  baseUrl: string;
  token?: string;
}

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function createApiClient(config: ClientConfig) {
  function headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (config.token) {
      h["Authorization"] = `Bearer ${config.token}`;
    }
    return h;
  }

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${config.baseUrl}${path}`, {
      ...init,
      headers: { ...headers(), ...init?.headers },
    });

    if (!response.ok) {
      const body: ApiErrorBody = await response.json();
      throw new ApiError(body.error.code, body.error.message, response.status);
    }

    return response.json() as Promise<T>;
  }

  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "POST", body: JSON.stringify(body) }),
    patch: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (path: string) => request<void>(path, { method: "DELETE" }),
  };
}
