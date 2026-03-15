import { beforeEach, describe, expect, it, vi } from "vitest";

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sends JSON requests for createWorkspace", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "ws-1", name: "Acme" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("./api");
    await api.createWorkspace({ name: "Acme" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Acme" }),
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });

  it("throws backend detail text for failed requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: "Forbidden",
        json: async () => ({ detail: "blocked" }),
      }),
    );

    const { api } = await import("./api");

    await expect(api.listWorkspaces()).rejects.toThrow("blocked");
  });

  it("uploads form data without forcing a JSON content-type", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "doc-1" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { api } = await import("./api");
    const form = new FormData();
    form.append("filename", "guide.md");

    await api.uploadDocument("ws-1", form);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/ws-1/documents",
      expect.objectContaining({
        method: "POST",
        body: form,
      }),
    );
  });
});
