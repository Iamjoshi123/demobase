import { expect, test, type APIRequestContext } from "@playwright/test";

async function getSeededWorkspaceId(request: APIRequestContext) {
  const response = await request.get("http://127.0.0.1:8100/api/workspaces");
  const workspaces = await response.json();
  const workspace = workspaces.find((item: { name: string }) => item.name === "Acme CRM Pro");

  if (!workspace) {
    throw new Error("Seeded workspace not found");
  }

  return workspace.id as string;
}

test.describe.configure({ mode: "serial" });

test("Journey A: admin opens the app, sees a created workspace, and adds a recipe", async ({ page, request }) => {
  const workspaceCreate = await request.post("http://127.0.0.1:8100/api/workspaces", {
    data: {
      name: "QA Workspace",
      description: "Workspace created from Playwright",
      product_url: "https://app.example.com",
      allowed_domains: "app.example.com",
    },
  });
  expect(workspaceCreate.ok()).toBeTruthy();
  const workspace = await workspaceCreate.json();

  await page.goto("/admin");
  await page.goto(`/admin/workspaces/${workspace.id}`);
  await expect(page.getByRole("heading", { name: "QA Workspace" })).toBeVisible();

  await page.getByRole("button", { name: /Recipes/ }).click();
  await page.getByPlaceholder("Recipe name").fill("QA Recipe");
  await page.getByPlaceholder("Description").fill("Created in e2e");
  await page.getByPlaceholder("Trigger phrases (comma-separated)").fill("qa recipe");
  await page.getByPlaceholder("Priority").fill("3");
  await page
    .getByPlaceholder('Steps JSON: [{"action":"navigate","target":"http://..."}]')
    .fill('[{"action":"navigate","target":"https://app.example.com/dashboard"}]');
  const recipeResponsePromise = page.waitForResponse(
    (response) => response.url().includes(`/api/workspaces/${workspace.id}/recipes`) && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Create Recipe" }).click();
  const recipeResponse = await recipeResponsePromise;
  expect(recipeResponse.ok()).toBeTruthy();

  await expect(page.getByText("QA Recipe", { exact: true })).toBeVisible();
});

test("Journey B: buyer gets a grounded answer and summary appears in admin", async ({ page, request }) => {
  const buyerName = "Journey Buyer";
  const seededWorkspaceId = await getSeededWorkspaceId(request);

  await page.goto("/demo/demo-acme-crm-001");
  await page.getByPlaceholder("Your name (optional)").fill(buyerName);
  await page.getByRole("button", { name: "Start Demo" }).click();
  await page.getByPlaceholder("Ask about the product...").fill("What integrations do you have?");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText(/Answering \+ showing demo/)).toBeVisible();
  await expect(page.getByText(/Test response based on docs:/)).toBeVisible();

  await page.getByRole("button", { name: "End Session" }).click();
  await expect(page.getByText(/Session ended\. Lead intent score:/)).toBeVisible();

  await page.goto(`/admin/workspaces/${seededWorkspaceId}/sessions`);
  await page.getByRole("button", { name: new RegExp(buyerName) }).click();
  await expect(page.getByText("Session Summary")).toBeVisible();
  await expect(page.getByText("What integrations do you have?", { exact: true })).toBeVisible();
});

test("Journey C: buyer asks a blocked pricing question and is escalated", async ({ page }) => {
  await page.goto("/demo/demo-acme-crm-001");
  await page.getByPlaceholder("Your name (optional)").fill("Pricing Buyer");
  await page.getByRole("button", { name: "Start Demo" }).click();
  await page.getByPlaceholder("Ask about the product...").fill("Can I get a discount on pricing?");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Connecting to sales team...")).toBeVisible();
  await expect(page.getByText("Escalated to sales team")).toBeVisible();
});

test("Journey D: seeded recipe execution updates the browser view and action log", async ({ page, request }) => {
  const buyerName = "Recipe Buyer";
  const seededWorkspaceId = await getSeededWorkspaceId(request);

  await page.goto("/demo/demo-acme-crm-001");
  await page.getByPlaceholder("Your name (optional)").fill(buyerName);
  await page.getByRole("button", { name: "Start Demo" }).click();
  await page.getByRole("button", { name: "Start Live Demo" }).click();
  await expect(page.getByText("Live Product Session", { exact: true })).toBeVisible();
  await expect(page.getByText("Video connected", { exact: true })).toBeVisible();

  await page.getByPlaceholder("Ask about the product...").fill("Show me the dashboard");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Answering + showing demo").first()).toBeVisible();
  await expect(page.getByText("Live Product Session", { exact: true })).toBeVisible();

  await page.goto(`/admin/workspaces/${seededWorkspaceId}/sessions`);
  await page.getByRole("button", { name: new RegExp(buyerName) }).click();
  await expect(page.getByText(/Browser Audit Trail/)).toBeVisible();
  await expect(page.getByText(/navigate/i)).toBeVisible();
});

test("Acceptance Journey: buyer validates docs grounding, live demo flow, and session summary", async ({ page, request }) => {
  const buyerName = "Acceptance Buyer";
  const seededWorkspaceId = await getSeededWorkspaceId(request);

  await page.goto(`/admin/workspaces/${seededWorkspaceId}`);
  await page.getByRole("button", { name: /Documents/ }).click();
  await expect(page.getByText("contacts-and-import.md")).toBeVisible();
  await expect(page.getByText("commercial-boundaries.md")).toBeVisible();

  await page.goto("/demo/demo-acme-crm-001");
  await page.getByPlaceholder("Your name (optional)").fill(buyerName);
  await page.getByRole("button", { name: "Start Demo" }).click();

  await page.getByPlaceholder("Ask about the product...").fill("Tell me about CSV import for contacts");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText(/Test response based on docs:/)).toBeVisible();
  await expect(page.getByText(/Contacts And CSV Import/i)).toBeVisible();

  await page.getByRole("button", { name: "Start Live Demo" }).click();
  await expect(page.getByText("Live Product Session", { exact: true })).toBeVisible();
  await expect(page.getByText("Video connected", { exact: true })).toBeVisible();

  await page.getByPlaceholder("Ask about the product...").fill("Show me the dashboard");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Answering + showing demo").first()).toBeVisible();
  await expect(page.getByText("Live Product Session", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "End Session" }).click();
  await expect(page.getByText(/Session ended\. Lead intent score:/)).toBeVisible();

  await page.goto(`/admin/workspaces/${seededWorkspaceId}/sessions`);
  await page.getByRole("button", { name: new RegExp(buyerName) }).click();
  await expect(page.getByText("Session Summary")).toBeVisible();
  await expect(page.getByText("Tell me about CSV import for contacts", { exact: true })).toBeVisible();
  await expect(page.getByText(/Browser Audit Trail/)).toBeVisible();
});
