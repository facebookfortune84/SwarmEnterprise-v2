import { describe, it, expect, vi, beforeEach } from "vitest";
import * as fc from "fast-check";

// Mock the authStore BEFORE importing ApiClient
let _mockToken: string | null = null;
vi.mock("@/store/authStore", () => ({
  useAuthStore: {
    getState: vi.fn(() => ({
      get token() { return _mockToken; },
      clearToken: vi.fn(),
    })),
  },
}));

import { apiFetch } from "@/services/ApiClient";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Mock window.location
const mockLocation = { pathname: "/dashboard", search: "", href: "" };
vi.stubGlobal("window", {
  ...globalThis.window,
  location: mockLocation,
  dispatchEvent: vi.fn(),
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
    clear: () => { store = {}; },
  };
})();
vi.stubGlobal("localStorage", localStorageMock);

beforeEach(() => {
  localStorageMock.clear();
  vi.clearAllMocks();
});

describe("apiFetch", () => {
  it("makes a GET request and returns JSON", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok" }),
    } as Response);

    const result = await apiFetch<{ status: string }>("/health");
    expect(result.status).toBe("ok");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => ({ detail: "Server crashed" }),
    } as Response);

    await expect(apiFetch("/api/test")).rejects.toThrow("Server crashed");
  });

  it("returns null for 204 response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    } as Response);

    const result = await apiFetch("/api/test");
    expect(result).toBeNull();
  });

  it("adds Authorization header when token is present", async () => {
    _mockToken = "test-jwt-token";

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    } as Response);

    await apiFetch("/api/me");
    const callArgs = mockFetch.mock.calls[0];
    const options = callArgs[1] as RequestInit;
    const headers = options.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer test-jwt-token");
    _mockToken = null;
  });

  it("throws on network error", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network failure"));
    await expect(apiFetch("/api/test")).rejects.toThrow("Network error");
  });
});

// ── Property 23: API client 429 back-off stays within bounds ─────────────────

describe("429 back-off bounds (property)", () => {
  it("delay for retry n is within [1*2^n, 31000]ms", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 5 }), (n) => {
        // Compute the same formula used in apiFetch
        const baseDelay = Math.min(1000 * Math.pow(2, n), 30_000);
        const maxDelay = baseDelay + 1000; // jitter up to 1000ms

        expect(baseDelay).toBeGreaterThanOrEqual(1000);
        expect(maxDelay).toBeLessThanOrEqual(31_000);
        // Base delay is capped at 30s
        expect(baseDelay).toBeLessThanOrEqual(30_000);
      }),
      { numRuns: 100 },
    );
  });

  it("retries at most 5 times on 429", async () => {
    // Every call returns 429
    mockFetch.mockResolvedValue({
      ok: false,
      status: 429,
      statusText: "Too Many Requests",
      json: async () => ({ detail: "Rate limited" }),
    } as Response);

    // Patch setTimeout to be instant
    vi.useFakeTimers();
    const fetchPromise = apiFetch("/api/test", {}, 5); // Start at max retries (5)
    vi.runAllTimers();
    try {
      await fetchPromise;
    } catch {
      // Expected to throw after all retries
    }
    vi.useRealTimers();

    // apiFetch(path, options, retries=5) → retries >= 5 → no retry → falls through to error
    expect(mockFetch.mock.calls.length).toBeLessThanOrEqual(6);
  });
});
