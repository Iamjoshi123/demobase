import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminAnalyticsPage from "./page";

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
  usePathname: () => "/admin/analytics",
  useSearchParams: () => new URLSearchParams("workspaceId=ws-1"),
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

describe("AdminAnalyticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.listWorkspaces.mockResolvedValue([{ id: "ws-1", name: "Saleshandy" }]);
    apiMock.getWorkspace.mockResolvedValue({ id: "ws-1", name: "Saleshandy", is_active: true });
    apiMock.getWorkspaceAnalytics.mockResolvedValue({
      workspace_id: "ws-1",
      total_sessions: 3,
      completed_sessions: 2,
      average_lead_score: 64,
      total_messages: 12,
      total_browser_actions: 6,
      top_questions: ["How do I set up sequences?"],
      features_interest: ["Sequences"],
      objections: ["Does it support agencies?"],
      sessions: [],
    });
    apiMock.getWorkspaceSessions.mockResolvedValue([
      { id: "sess-1", buyer_name: "Taylor Buyer", status: "ended", mode: "live", started_at: "2026-03-17T02:00:00.000Z", ended_at: "2026-03-17T02:08:00.000Z" },
    ]);
    apiMock.getSessionSummary.mockResolvedValue({
      id: "sum-1",
      session_id: "sess-1",
      summary_text: "Taylor Buyer explored sequences.",
      top_questions: JSON.stringify(["How do I set up sequences?"]),
      features_interest: JSON.stringify(["Sequences"]),
      objections: JSON.stringify(["Does it support agencies?"]),
      unresolved_items: JSON.stringify([]),
      escalation_reasons: JSON.stringify([]),
      lead_intent_score: 81,
      total_messages: 6,
      total_actions: 3,
      duration_seconds: 480,
      created_at: "2026-03-17T02:08:00.000Z",
    });
  });

  it("renders detailed report sections", async () => {
    render(<AdminAnalyticsPage />);

    expect(await screen.findByText("Question themes")).toBeInTheDocument();
    expect(screen.getByText("Highest intent sessions")).toBeInTheDocument();
    expect(screen.getByText("How do I set up sequences")).toBeInTheDocument();
  });
});
