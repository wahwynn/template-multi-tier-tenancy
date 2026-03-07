import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

describe("API client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("sends Authorization header when token is provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: [] }),
    });

    const { createApiClient } = await import("@/lib/api");
    const client = createApiClient({ baseUrl: "http://localhost:8000", token: "test-token" });
    await client.get("/v1/org/units/");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/org/units/",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    );
  });

  it("throws ApiError with error code on non-2xx response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ error: { code: "not_found", message: "Not found" } }),
    });

    const { createApiClient, ApiError } = await import("@/lib/api");
    const client = createApiClient({ baseUrl: "http://localhost:8000" });
    await expect(client.get("/v1/org/units/999/")).rejects.toThrow(ApiError);
  });

  it("omits Authorization header when no token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    const { createApiClient } = await import("@/lib/api");
    const client = createApiClient({ baseUrl: "http://localhost:8000" });
    await client.get("/v1/auth/token/");

    const callArgs = mockFetch.mock.calls[0][1];
    expect(callArgs.headers).not.toHaveProperty("Authorization");
  });
});
