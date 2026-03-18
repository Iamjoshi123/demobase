import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminPage from "./page";

const pushMock = vi.fn();
const replaceMock = vi.fn();

const apiMock = vi.hoisted(() => ({
  listWorkspaces: vi.fn(),
  getWorkspace: vi.fn(),
  getWorkspaceAnalytics: vi.fn(),
  getWorkspaceSessions: vi.fn(),
  getSessionSummary: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin",
  useSearchParams: () => new URLSearchParams("workspaceId=ws-1"),
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

describe("AdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.listWorkspaces.mockResolvedValue([
      {
        id: "ws-1",
        name: "Saleshandy",
        description: "Outbound sales engagement",
        product_url: "https://app.saleshandy.com",
        allowed_domains: "app.saleshandy.com",
        browser_auth_mode: "credentials",
        public_token: "demo-saleshandy-001",
        is_active: true,
        created_at: "2026-03-17T00:00:00.000Z",
        updated_at: "2026-03-17T00:00:00.000Z",
      },
    ]);
    apiMock.getWorkspace.mockResolvedValue({
      id: "ws-1",
      name: "Saleshandy",
      description: "Outbound sales engagement",
      product_url: "https://app.saleshandy.com",
      allowed_domains: "app.saleshandy.com",
      browser_auth_mode: "credentials",
      public_token: "demo-saleshandy-001",
      is_active: true,
    });
    apiMock.getWorkspaceAnalytics.mockResolvedValue({
      workspace_id: "ws-1",
      total_sessions: 12,
      completed_sessions: 9,
      average_lead_score: 68,
      total_messages: 46,
      total_browser_actions: 20,
      top_questions: ["How do I set up sequences?"],
      features_interest: ["Sequences"],
      objections: ["Do you support agencies?"],
      sessions: [],
    });
    apiMock.getWorkspaceSessions.mockResolvedValue([
      {
        id: "sess-1",
        buyer_name: "Taylor Buyer",
        status: "ended",
        mode: "live",
        started_at: "2026-03-17T02:00:00.000Z",
        ended_at: "2026-03-17T02:08:00.000Z",
      },
    ]);
    apiMock.getSessionSummary.mockResolvedValue({
      id: "sum-1",
      session_id: "sess-1",
      summary_text: "Taylor Buyer explored sequences and asked about setup.",
      top_questions: JSON.stringify(["How do I set up sequences?"]),
      features_interest: JSON.stringify(["Sequences"]),
      objections: JSON.stringify(["Do you support agencies?"]),
      unresolved_items: JSON.stringify(["Can I white-label reports?"]),
      escalation_reasons: JSON.stringify([]),
      lead_intent_score: 82,
      total_messages: 8,
      total_actions: 4,
      duration_seconds: 480,
      created_at: "2026-03-17T02:08:00.000Z",
    });
  });

  it("renders the dashboard as the admin home with report panels", async () => {
    render(<AdminPage />);

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Recent sessions" })).toBeInTheDocument();
    expect(screen.getByText("How do I set up sequences")).toBeInTheDocument();
    expect(screen.getByText("Intent Signals")).toBeInTheDocument();
  });

  it("loads workspace report data for the selected product", async () => {
    render(<AdminPage />);

    await waitFor(() => {
      expect(apiMock.getWorkspaceAnalytics).toHaveBeenCalledWith("ws-1");
      expect(apiMock.getWorkspaceSessions).toHaveBeenCalledWith("ws-1");
    });
  });
});
