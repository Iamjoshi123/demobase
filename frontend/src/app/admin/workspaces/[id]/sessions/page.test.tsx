import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SessionsPage from "./page";

const apiMock = vi.hoisted(() => ({
  getWorkspaceSessions: vi.fn(),
  getSession: vi.fn(),
  getMessages: vi.fn(),
  getSessionActions: vi.fn(),
  getSessionSummary: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "ws-1" }),
  useSearchParams: () => ({
    get: () => "sess-1",
  }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

describe("SessionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getWorkspaceSessions.mockResolvedValue([
      {
        id: "sess-1",
        buyer_name: "Taylor Buyer",
        status: "ended",
        started_at: "2026-03-08T00:00:00.000Z",
        lead_intent_score: 72,
      },
    ]);
    apiMock.getSession.mockResolvedValue({
      id: "sess-1",
      buyer_name: "Taylor Buyer",
      status: "ended",
    });
    apiMock.getMessages.mockResolvedValue([
      { id: "m1", role: "user", content: "Show me the dashboard", created_at: "2026-03-08T00:00:00.000Z" },
      { id: "m2", role: "agent", content: "Here it is", planner_decision: "answer_and_demo", created_at: "2026-03-08T00:00:01.000Z" },
    ]);
    apiMock.getSessionActions.mockResolvedValue([
      { id: "a1", action_type: "navigate", status: "success", narration: "Opened dashboard", duration_ms: 120 },
    ]);
    apiMock.getSessionSummary.mockResolvedValue({
      summary_text: "Taylor Buyer explored reporting and dashboards.",
      lead_intent_score: 72,
      total_messages: 2,
      total_actions: 1,
      top_questions: JSON.stringify(["Show me the dashboard"]),
    });
  });

  it("renders the session summary, transcript, and browser actions", async () => {
    render(<SessionsPage />);

    expect(await screen.findByText("Session Summary")).toBeInTheDocument();
    expect(screen.getByText("Taylor Buyer explored reporting and dashboards.")).toBeInTheDocument();
    expect(screen.getByText("Transcript")).toBeInTheDocument();
    expect(screen.getByText("Show me the dashboard")).toBeInTheDocument();
    expect(screen.getByText("[answer_and_demo]")).toBeInTheDocument();
    expect(screen.getByText(/Browser Audit Trail/)).toBeInTheDocument();
    expect(screen.getByText("Opened dashboard")).toBeInTheDocument();
  });

  it("loads another session when the user selects it", async () => {
    apiMock.getWorkspaceSessions.mockResolvedValueOnce([
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

    render(<SessionsPage />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /Jordan Prospect/i }));

    await waitFor(() => {
      expect(apiMock.getSession).toHaveBeenCalledWith("sess-2");
    });
  });
});
