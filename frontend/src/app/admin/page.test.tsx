import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminPage from "./page";

const apiMock = vi.hoisted(() => ({
  listWorkspaces: vi.fn(),
  createWorkspace: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

describe("AdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the empty state after loading", async () => {
    apiMock.listWorkspaces.mockResolvedValueOnce([]);

    render(<AdminPage />);

    expect(screen.getByText("Loading workspaces...")).toBeInTheDocument();
    expect(await screen.findByText(/No workspaces yet/)).toBeInTheDocument();
  });

  it("creates a workspace and reloads the list", async () => {
    apiMock.listWorkspaces
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: "ws-1",
          name: "Acme CRM",
          description: "Demo workspace",
          browser_auth_mode: "credentials",
          public_token: "token-123",
          created_at: "2026-03-08T00:00:00.000Z",
        },
      ]);
    apiMock.createWorkspace.mockResolvedValueOnce({ id: "ws-1" });

    render(<AdminPage />);
    const user = userEvent.setup();

    await user.click((await screen.findAllByRole("button", { name: /\+ New Workspace/i }))[0]);
    await user.type(screen.getByPlaceholderText("e.g., Acme CRM Pro"), "Acme CRM");
    await user.type(screen.getByPlaceholderText("Brief product description..."), "Demo workspace");
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(apiMock.createWorkspace).toHaveBeenCalledWith({
        name: "Acme CRM",
        description: "Demo workspace",
        product_url: "",
        allowed_domains: "",
        browser_auth_mode: "credentials",
      });
    });
    expect(await screen.findByText("Acme CRM")).toBeInTheDocument();
  });

  it("marks the required name field on the create form", async () => {
    apiMock.listWorkspaces.mockResolvedValueOnce([]);

    render(<AdminPage />);
    const user = userEvent.setup();

    await user.click((await screen.findAllByRole("button", { name: /\+ New Workspace/i }))[0]);

    expect(screen.getByPlaceholderText("e.g., Acme CRM Pro")).toBeRequired();
  });
});
