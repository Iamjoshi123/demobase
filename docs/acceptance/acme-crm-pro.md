# Acme CRM Pro Acceptance Runbook

This runbook exercises the product the way a real buyer and admin would use it.

## Goal

Validate one complete buyer-demo workflow locally:

1. Admin reviews the seeded workspace and source material.
2. Buyer asks a grounded product question.
3. Buyer starts a live demo and sees a browser-backed walkthrough.
4. Buyer asks a pricing question and gets escalated.
5. Admin reviews the finished session summary and audit trail.

## Fixture Pack

The default seed script loads the acceptance scenario from:

- `fixtures/acceptance/acme-crm-pro/product-overview.md`
- `fixtures/acceptance/acme-crm-pro/contacts-and-import.md`
- `fixtures/acceptance/acme-crm-pro/reporting-and-analytics.md`
- `fixtures/acceptance/acme-crm-pro/commercial-boundaries.md`

## Recommended Local Mode

Use deterministic local fallbacks first. This avoids real provider keys while still exercising the real frontend and backend.

```powershell
$env:APP_ENV="test"
$env:DATABASE_URL="sqlite:///./acceptance.db"
$env:FRONTEND_URL="http://127.0.0.1:3000"
$env:BACKEND_URL="http://127.0.0.1:8000"
$env:ENCRYPTION_KEY="rHtpqtHXdq8jToWMunn1ep1jI2iw39QnpPRy01JCL5g="
```

## Seed And Start

Backend terminal:

```powershell
cd backend
if (Test-Path acceptance.db) { Remove-Item acceptance.db -Force }
C:/Python313/python.exe -m pip install -r requirements.txt
C:/Python313/python.exe -m app.seed
C:/Python313/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
cd frontend
npm install
npm run dev
```

## URLs

- Admin: `http://127.0.0.1:3000/admin`
- Demo: `http://127.0.0.1:3000/demo/demo-acme-crm-001`
- API Docs: `http://127.0.0.1:8000/docs`

## Manual Acceptance Flow

### 1. Admin review

Open the seeded workspace and confirm:

- Workspace name: `Acme CRM Pro`
- Documents tab shows the four fixture documents
- Recipes tab shows dashboard, search, create contact, edit record, and analytics recipes
- Policies tab shows pricing escalation and blocked admin or billing routes

### 2. Buyer grounded answer

Open the public demo link and start a session.

Ask:

`Tell me about CSV import for contacts`

Expected result:

- The answer is grounded in the contact import document
- The response mentions `CSV` and `Contacts`
- No escalation or refusal occurs

### 3. Buyer live demo

Click `Start Live Demo`.

Ask:

`Show me the dashboard`

Expected result:

- Agent status moves into demo mode
- Browser viewport appears
- A browser action trail is created for the session

### 4. Pricing escalation

Ask:

`Can I get an annual discount?`

Expected result:

- The agent escalates instead of inventing pricing
- The transcript clearly says the request is being routed to sales

### 5. Session close and admin review

Click `End Session`, then open the workspace session history in admin.

Expected result:

- Session summary exists
- Transcript contains the grounded question and the pricing escalation
- Browser audit trail shows the demo actions

## Automated Smoke Check

Run the same scenario as a Playwright smoke test:

```powershell
npm run test:acceptance
```

Or from the repo root:

```powershell
npm run test:acceptance
```

## Optional Higher-Fidelity Mode

Once the deterministic path is solid, switch from `APP_ENV=test` to a local/provider-backed mode and rerun the same runbook. That is the right point to evaluate answer quality, not before the product path itself is stable.
