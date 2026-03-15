import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceDetailPage from "./page";

const apiMock = vi.hoisted(() => ({
  getWorkspace: vi.fn(),
  listDocuments: vi.fn(),
  listCredentials: vi.fn(),
  listRecipes: vi.fn(),
  listPolicies: vi.fn(),
  getWorkspaceSessions: vi.fn(),
  createPolicy: vi.fn(),
  createRecipe: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "ws-1" }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

describe("WorkspaceDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getWorkspace.mockResolvedValue({
      id: "ws-1",
      name: "Acme CRM",
      description: "Demo workspace",
      public_token: "token-123",
    });
    apiMock.listDocuments.mockResolvedValue([{ id: "doc-1", filename: "guide.md", file_type: "md", status: "ready" }]);
    apiMock.listCredentials.mockResolvedValue([{ id: "cred-1", label: "demo-user-1", login_url: "https://app.example.com/login", is_active: true }]);
    apiMock.listRecipes.mockResolvedValue([{ id: "recipe-1", name: "Dashboard Tour", description: "Open dashboard", trigger_phrases: "dashboard", priority: 5 }]);
    apiMock.listPolicies.mockResolvedValue([{ id: "policy-1", description: "Block pricing", rule_type: "blocked_topic", action: "escalate", pattern: "pricing", severity: "high" }]);
    apiMock.getWorkspaceSessions.mockResolvedValue([{ id: "sess-1", buyer_name: "Taylor Buyer", status: "ended", started_at: "2026-03-08T00:00:00.000Z", lead_intent_score: 71 }]);
    apiMock.createPolicy.mockResolvedValue({ id: "policy-2" });
    apiMock.createRecipe.mockResolvedValue({ id: "recipe-2" });
  });

  it("renders overview counts and can add a policy rule", async () => {
    apiMock.listPolicies
      .mockResolvedValueOnce([{ id: "policy-1", description: "Block pricing", rule_type: "blocked_topic", action: "escalate", pattern: "pricing", severity: "high" }])
      .mockResolvedValueOnce([
        { id: "policy-1", description: "Block pricing", rule_type: "blocked_topic", action: "escalate", pattern: "pricing", severity: "high" },
        { id: "policy-2", description: "Escalate procurement", rule_type: "escalation_condition", action: "escalate", pattern: "procurement", severity: "medium" },
      ]);

    render(<WorkspaceDetailPage />);
    const user = userEvent.setup();

    expect(await screen.findByText("Acme CRM")).toBeInTheDocument();
    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("Credentials")).toBeInTheDocument();
    expect(screen.getByText("Recipes")).toBeInTheDocument();
    expect(screen.getByText("Sessions")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Policies/ }));
    await user.selectOptions(screen.getAllByRole("combobox")[0], "escalation_condition");
    await user.selectOptions(screen.getAllByRole("combobox")[1], "escalate");
    await user.selectOptions(screen.getAllByRole("combobox")[2], "medium");
    await user.type(screen.getByPlaceholderText("Pattern (regex)"), "procurement");
    await user.type(screen.getByPlaceholderText("Description"), "Escalate procurement");
    await user.click(screen.getByRole("button", { name: "Add Policy" }));

    await waitFor(() => {
      expect(apiMock.createPolicy).toHaveBeenCalledWith("ws-1", {
        rule_type: "escalation_condition",
        pattern: "procurement",
        description: "Escalate procurement",
        action: "escalate",
        severity: "medium",
      });
    });
    expect(await screen.findByText("Escalate procurement")).toBeInTheDocument();
  });

  it("creates a recipe from the admin flow", async () => {
    apiMock.listRecipes
      .mockResolvedValueOnce([{ id: "recipe-1", name: "Dashboard Tour", description: "Open dashboard", trigger_phrases: "dashboard", priority: 5 }])
      .mockResolvedValueOnce([
        { id: "recipe-1", name: "Dashboard Tour", description: "Open dashboard", trigger_phrases: "dashboard", priority: 5 },
        { id: "recipe-2", name: "Create Contact", description: "Show contact creation", trigger_phrases: "create contact", priority: 4 },
      ]);

    render(<WorkspaceDetailPage />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /Recipes/ }));
    await user.type(screen.getByPlaceholderText("Recipe name"), "Create Contact");
    await user.type(screen.getByPlaceholderText("Description"), "Show contact creation");
    await user.type(screen.getByPlaceholderText("Trigger phrases (comma-separated)"), "create contact");
    await user.clear(screen.getByPlaceholderText("Priority"));
    await user.type(screen.getByPlaceholderText("Priority"), "4");
    fireEvent.change(screen.getByPlaceholderText('Steps JSON: [{"action":"navigate","target":"http://..."}]'), {
      target: { value: '[{"action":"navigate","target":"https://app.example.com/contacts/new"}]' },
    });
    await user.click(screen.getByRole("button", { name: "Create Recipe" }));

    await waitFor(() => {
      expect(apiMock.createRecipe).toHaveBeenCalledWith("ws-1", {
        name: "Create Contact",
        description: "Show contact creation",
        trigger_phrases: "create contact",
        steps_json: '[{"action":"navigate","target":"https://app.example.com/contacts/new"}]',
        priority: 4,
      });
    });
    expect(await screen.findByText("Create Contact")).toBeInTheDocument();
  });
});
