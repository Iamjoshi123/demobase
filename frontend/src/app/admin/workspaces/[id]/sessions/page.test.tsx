import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminSessionsPage from "../../../sessions/page";

const pushMock = vi.fn();
const replaceMock = vi.fn();

const apiMock = vi.hoisted(() => ({
  listWorkspaces: vi.fn(),
  getWorkspace: vi.fn(),
  getWorkspaceAnalytics: vi.fn(),
  getWorkspaceSessions: vi.fn(),
  getMessages: vi.fn(),
  getSessionActions: vi.fn(),
  getSessionSummary: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin/sessions",
  useSearchParams: () => new URLSearchParams("workspaceId=ws-1&session=sess-1"),
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

describe("AdminSessionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.listWorkspaces.mockResolvedValue([{ id: "ws-1", name: "Acme CRM" }]);
    apiMock.getWorkspace.mockResolvedValue({ id: "ws-1", name: "Acme CRM" });
    apiMock.getWorkspaceAnalytics.mockResolvedValue({
      workspace_id: "ws-1",
      total_sessions: 2,
      completed_sessions: 1,
      average_lead_score: 56,
      total_messages: 6,
      total_browser_actions: 2,
      top_questions: ["Show me the dashboard"],
      features_interest: ["Reporting"],
      objections: [],
      sessions: [],
    });
    apiMock.getWorkspaceSessions.mockResolvedValue([
      {
        id: "sess-1",
        buyer_name: "Taylor Buyer",
        status: "ended",
        started_at: "2026-03-08T00:00:00.000Z",
        lead_intent_score: 72,
      },
      {
        id: "sess-2",
        buyer_name: "Jordan Prospect",
        status: "active",
        started_at: "2026-03-08T01:00:00.000Z",
        lead_intent_score: 40,
      },
    ]);
    apiMock.getMessages.mockResolvedValue([
      { id: "m1", role: "user", content: "Show me the dashboard", created_at: "2026-03-08T00:00:00.000Z" },
      { id: "m2", role: "agent", content: "Here it is", planner_decision: "answer_and_demo", created_at: "2026-03-08T00:00:01.000Z" },
    ]);
    apiMock.getSessionActions.mockResolvedValue([
      { id: "a1", action_type: "navigate", status: "success", narration: "Opened dashboard", duration_ms: 120, created_at: "2026-03-08T00:00:02.000Z" },
    ]);
    apiMock.getSessionSummary.mockResolvedValue({
      id: "sum-1",
      session_id: "sess-1",
      summary_text: "Taylor Buyer explored reporting and dashboards.",
      lead_intent_score: 72,
      total_messages: 2,
      total_actions: 1,
      top_questions: JSON.stringify(["Show me the dashboard"]),
      features_interest: JSON.stringify(["Dashboard"]),
      objections: JSON.stringify([]),
      unresolved_items: JSON.stringify(["Can I export reports?"]),
      escalation_reasons: JSON.stringify([]),
      duration_seconds: 240,
      created_at: "2026-03-08T00:04:00.000Z",
    });
  });

  it("renders the detailed session report, transcript, and insights", async () => {
    render(<AdminSessionsPage />);

    expect((await screen.findAllByText("Taylor Buyer explored reporting and dashboards.")).length).toBeGreaterThan(0);
    expect(screen.getByText("Show me the dashboard")).toBeInTheDocument();
    expect(screen.getByText(/Unanswered questions/i)).toBeInTheDocument();
    expect(screen.getByText(/Can I export reports/)).toBeInTheDocument();
    expect(screen.getByText(/Opened dashboard/)).toBeInTheDocument();
  });

  it("loads another session when the user selects it", async () => {
    render(<AdminSessionsPage />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /Jordan Prospect/i }));

    await waitFor(() => {
      expect(apiMock.getMessages).toHaveBeenCalledWith("sess-2");
    });
  });
});
