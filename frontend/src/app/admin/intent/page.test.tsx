import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminIntentPage from "./page";

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
  usePathname: () => "/admin/intent",
  useSearchParams: () => new URLSearchParams("workspaceId=ws-1"),
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

describe("AdminIntentPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.listWorkspaces.mockResolvedValue([{ id: "ws-1", name: "Saleshandy" }]);
    apiMock.getWorkspace.mockResolvedValue({ id: "ws-1", name: "Saleshandy", is_active: true });
    apiMock.getWorkspaceAnalytics.mockResolvedValue({
      workspace_id: "ws-1",
      total_sessions: 2,
      completed_sessions: 2,
      average_lead_score: 58,
      total_messages: 12,
      total_browser_actions: 6,
      top_questions: ["How much does it cost?"],
      features_interest: ["Sequences"],
      objections: ["I am confused about onboarding."],
      sessions: [],
    });
    apiMock.getWorkspaceSessions.mockResolvedValue([
      { id: "sess-1", buyer_name: "Taylor Buyer", status: "ended", mode: "live", started_at: "2026-03-17T02:00:00.000Z", ended_at: "2026-03-17T02:08:00.000Z" },
      { id: "sess-2", buyer_name: "Jordan Prospect", status: "ended", mode: "live", started_at: "2026-03-16T01:00:00.000Z", ended_at: "2026-03-16T01:01:00.000Z" },
    ]);
    apiMock.getSessionSummary
      .mockResolvedValueOnce({
        id: "sum-1",
        session_id: "sess-1",
        summary_text: "Taylor Buyer asked about pricing and wanted a human follow-up.",
        top_questions: JSON.stringify(["How much does it cost?", "Can I start a trial?"]),
        features_interest: JSON.stringify(["Sequences", "Team seats", "Onboarding"]),
        objections: JSON.stringify([]),
        unresolved_items: JSON.stringify([]),
        escalation_reasons: JSON.stringify(["Asked for a sales call"]),
        lead_intent_score: 88,
        total_messages: 8,
        total_actions: 4,
        duration_seconds: 1020,
        created_at: "2026-03-17T02:08:00.000Z",
      })
      .mockResolvedValueOnce({
        id: "sum-2",
        session_id: "sess-2",
        summary_text: "Jordan Prospect seemed confused and left early.",
        top_questions: JSON.stringify(["How does onboarding work?"]),
        features_interest: JSON.stringify(["Onboarding"]),
        objections: JSON.stringify(["I am confused about onboarding."]),
        unresolved_items: JSON.stringify(["How does onboarding work?"]),
        escalation_reasons: JSON.stringify([]),
        lead_intent_score: 28,
        total_messages: 4,
        total_actions: 1,
        duration_seconds: 60,
        created_at: "2026-03-16T01:01:00.000Z",
      });
  });

  it("renders intent indicators and negative patterns", async () => {
    render(<AdminIntentPage />);

    expect(await screen.findByText("Intent indicators")).toBeInTheDocument();
    expect(screen.getByText("Requested human follow-up")).toBeInTheDocument();
    expect(screen.getByText("Early abandonment")).toBeInTheDocument();
  });
});
