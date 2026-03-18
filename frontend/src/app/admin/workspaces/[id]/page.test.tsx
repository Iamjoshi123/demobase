import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProductDetailPage from "../../products/[id]/page";

const apiMock = vi.hoisted(() => ({
  listWorkspaces: vi.fn(),
  getWorkspace: vi.fn(),
  listDocuments: vi.fn(),
  listCredentials: vi.fn(),
  listRecipes: vi.fn(),
  listPolicies: vi.fn(),
  getWorkspaceSessions: vi.fn(),
  updateWorkspace: vi.fn(),
  createPolicy: vi.fn(),
  createRecipe: vi.fn(),
  getSession: vi.fn(),
  getMessages: vi.fn(),
  getSessionActions: vi.fn(),
  getSessionSummary: vi.fn(),
}));

const pushMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin/products/ws-1",
  useParams: () => ({ id: "ws-1" }),
  useSearchParams: () => new URLSearchParams(""),
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

describe("ProductDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.listWorkspaces.mockResolvedValue([
      {
        id: "ws-1",
        name: "Acme CRM",
        description: "Demo workspace",
        product_url: "https://app.example.com",
        allowed_domains: "app.example.com",
        browser_auth_mode: "credentials",
        public_token: "token-123",
        is_active: true,
      },
    ]);
    apiMock.getWorkspace.mockResolvedValue({
      id: "ws-1",
      name: "Acme CRM",
      description: "Demo workspace",
      product_url: "https://app.example.com",
      allowed_domains: "app.example.com",
      browser_auth_mode: "credentials",
      public_token: "token-123",
      is_active: true,
    });
    apiMock.listDocuments.mockResolvedValue([{ id: "doc-1", filename: "guide.md", file_type: "md", status: "ready" }]);
    apiMock.listCredentials.mockResolvedValue([{ id: "cred-1", label: "demo-user-1", login_url: "https://app.example.com/login", is_active: true }]);
    apiMock.listRecipes.mockResolvedValue([{ id: "recipe-1", name: "Dashboard Tour", description: "Open dashboard", trigger_phrases: "dashboard", priority: 5 }]);
    apiMock.listPolicies.mockResolvedValue([{ id: "policy-1", description: "Block pricing", rule_type: "blocked_topic", action: "escalate", pattern: "pricing", severity: "high" }]);
    apiMock.getWorkspaceSessions.mockResolvedValue([{ id: "sess-1", buyer_name: "Taylor Buyer", status: "ended", started_at: "2026-03-08T00:00:00.000Z", lead_intent_score: 71 }]);
    apiMock.createPolicy.mockResolvedValue({ id: "policy-2" });
    apiMock.createRecipe.mockResolvedValue({ id: "recipe-2" });
    apiMock.getMessages.mockResolvedValue([{ id: "m1", role: "user", content: "Show me dashboard", created_at: "2026-03-08T00:00:00.000Z" }]);
    apiMock.getSessionActions.mockResolvedValue([{ id: "a1", action_type: "navigate", narration: "Opened dashboard", created_at: "2026-03-08T00:00:02.000Z" }]);
    apiMock.getSessionSummary.mockResolvedValue({
      id: "sum-1",
      session_id: "sess-1",
      summary_text: "Taylor Buyer explored dashboards.",
      top_questions: JSON.stringify(["Show me dashboard"]),
      features_interest: JSON.stringify(["Reporting workflow"]),
      objections: JSON.stringify([]),
      unresolved_items: JSON.stringify([]),
      escalation_reasons: JSON.stringify([]),
      lead_intent_score: 71,
      total_messages: 4,
      total_actions: 1,
      duration_seconds: 360,
      created_at: "2026-03-08T00:06:00.000Z",
    });
  });

  it("renders the new product tabs and can add a policy rule", async () => {
    apiMock.listPolicies
      .mockResolvedValueOnce([{ id: "policy-1", description: "Block pricing", rule_type: "blocked_topic", action: "escalate", pattern: "pricing", severity: "high" }])
      .mockResolvedValueOnce([
        { id: "policy-1", description: "Block pricing", rule_type: "blocked_topic", action: "escalate", pattern: "pricing", severity: "high" },
        { id: "policy-2", description: "Escalate procurement", rule_type: "escalation_condition", action: "escalate", pattern: "procurement", severity: "medium" },
      ]);

    render(<ProductDetailPage />);
    const user = userEvent.setup();

    expect(await screen.findByRole("heading", { name: "Acme CRM" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Share" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Agent" }));
    const comboboxes = screen.getAllByRole("combobox");
    await user.selectOptions(comboboxes[1], "escalation_condition");
    await user.selectOptions(comboboxes[2], "escalate");
    await user.selectOptions(comboboxes[3], "medium");
    await user.type(screen.getByPlaceholderText("Pattern"), "procurement");
    await user.type(screen.getAllByPlaceholderText("Description")[0], "Escalate procurement");
    await user.click(screen.getByRole("button", { name: "Add policy" }));

    await waitFor(() => {
      expect(apiMock.createPolicy).toHaveBeenCalledWith("ws-1", {
        rule_type: "escalation_condition",
        pattern: "procurement",
        description: "Escalate procurement",
        action: "escalate",
        severity: "medium",
      });
    });
  });

  it("creates a recipe from the agent tab", async () => {
    apiMock.listRecipes
      .mockResolvedValueOnce([{ id: "recipe-1", name: "Dashboard Tour", description: "Open dashboard", trigger_phrases: "dashboard", priority: 5 }])
      .mockResolvedValueOnce([
        { id: "recipe-1", name: "Dashboard Tour", description: "Open dashboard", trigger_phrases: "dashboard", priority: 5 },
        { id: "recipe-2", name: "Create Contact", description: "Show contact creation", trigger_phrases: "create contact", priority: 4 },
      ]);

    render(<ProductDetailPage />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Agent" }));
    await user.type(screen.getByPlaceholderText("Recipe name"), "Create Contact");
    await user.type(screen.getAllByPlaceholderText("Description")[1], "Show contact creation");
    await user.type(screen.getByPlaceholderText("Trigger phrases"), "create contact");
    await user.clear(screen.getByPlaceholderText("Priority"));
    await user.type(screen.getByPlaceholderText("Priority"), "4");
    fireEvent.change(screen.getByPlaceholderText('[{"action":"navigate","target":"https://app.example.com"}]'), {
      target: { value: '[{"action":"navigate","target":"https://app.example.com/contacts/new"}]' },
    });
    await user.click(screen.getByRole("button", { name: "Create recipe" }));

    await waitFor(() => {
      expect(apiMock.createRecipe).toHaveBeenCalledWith("ws-1", {
        name: "Create Contact",
        description: "Show contact creation",
        trigger_phrases: "create contact",
        steps_json: '[{"action":"navigate","target":"https://app.example.com/contacts/new"}]',
        priority: 4,
      });
    });
  });
});
