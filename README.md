# Agentic Demo Brain

Agentic Demo Brain is a live product-demo stack for B2B SaaS.

It lets a buyer open a shareable demo link, talk to an AI agent, ask product questions, and watch the agent drive a real or sandboxed product in the browser. The system combines:

- a Next.js buyer/admin frontend
- a FastAPI backend
- browser automation through Playwright and Stagehand
- live voice and browser media over LiveKit
- retrieval over seeded product docs and policies

## What This Repo Is Used For

Use this repo when you want to:

- create public demo links for a product workspace
- let buyers ask questions in chat or voice
- show a guided live walkthrough while the agent speaks
- enforce guardrails for pricing, billing, admin, or destructive routes
- capture session transcripts and summaries after the demo

Seeded examples in this repo:

- `demo-acme-crm-001`
- `demo-saleshandy-001`

Common local URLs:

- buyer demo: `http://localhost:3000/demo/<token>`
- live meeting: `http://localhost:3000/meet/<token>`
- admin: `http://localhost:3000/admin`
- backend docs: `http://localhost:8000/docs`

## Architecture

High-level flow:

1. The frontend creates or joins a meeting from a public token.
2. The backend loads workspace docs, recipes, and policies.
3. The planner decides whether to answer, walk through, or escalate.
4. The live runtime drives the browser and streams media through LiveKit.
5. The frontend renders the live stage and the conversation side by side.

Main folders:

- `backend/` FastAPI app, orchestration, browser runtime, live media, tests
- `frontend/` Next.js app, meeting pages, admin pages, Vitest and Playwright tests
- `fixtures/` seeded product documentation and acceptance fixtures
- `docs/` acceptance runbooks and architecture notes
- `stagehand-bridge/` local Node bridge used for Stagehand automation
- `scripts/` Windows helpers for starting local or cloud-backed runs
- `infra/` local LiveKit config

## Tech Stack

- Backend: Python 3.13, FastAPI, SQLModel, Pydantic Settings, Uvicorn
- Frontend: Next.js 14, React 18, TypeScript
- Browser automation: Playwright, Stagehand
- Voice and media: LiveKit, LiveKit Agents, OpenAI Realtime or local voice path
- Retrieval: Qdrant, optional sentence-transformers, optional Docling
- Testing: Pytest, Vitest, Playwright
- Local orchestration: Docker Compose, Windows `.cmd` helpers, Makefile

## Prerequisites

Recommended local setup:

- Python 3.13 at `C:\Python313\python.exe`
- Node.js 18+
- npm
- Docker Desktop if you want local Qdrant and local LiveKit
- Chromium dependencies for Playwright

Install Playwright browser once:

```powershell
cd backend
C:\Python313\python.exe -m playwright install chromium
```

## Environment Setup

1. Copy `.env.example` to `.env`.
2. Set a real `ENCRYPTION_KEY`.
3. Choose your media path:
   - local LiveKit in Docker
   - LiveKit Cloud
4. Choose your model path:
   - local or optional providers for backend planning
   - OpenAI Realtime if you want the full live voice path

Important env vars:

- `DATABASE_URL`
- `QDRANT_URL`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `ENCRYPTION_KEY`
- `ENABLE_STAGEHAND`
- `STAGEHAND_BRIDGE_URL`
- `ENABLE_VOICE`
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` when relevant

See [`.env.example`](/c:/Users/Lenovo/OneDrive/Desktop/demobase/.env.example) for the full list.

## Run Locally

### Option 1: Basic local dev

Install dependencies:

```powershell
cd backend
C:\Python313\python.exe -m pip install -r requirements.txt

cd ..\frontend
npm install

cd ..
npm install
```

Start infra:

```powershell
docker compose up -d qdrant livekit
```

Seed the demo data:

```powershell
cd backend
C:\Python313\python.exe -m app.seed
```

Start backend:

```powershell
cd backend
C:\Python313\python.exe run.py
```

Start frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

- `http://localhost:3000/demo/demo-acme-crm-001`
- `http://localhost:3000/meet/demo-saleshandy-001`

### Option 2: One-command local Stagehand flow

This path starts:

- Stagehand bridge
- backend with Stagehand enabled
- frontend dev server

Run:

```powershell
scripts\start-local-stagehand.cmd
```

Logs are written to the repo root:

- `backend-out.log`
- `backend-err.log`
- `frontend-out.log`
- `frontend-err.log`
- `stagehand-bridge-out.log`
- `stagehand-bridge-err.log`

### Option 3: Docker Compose full stack

```powershell
docker compose up --build
```

This is useful for quick backend/frontend/Qdrant/LiveKit bootstrapping, but the most realistic live browser + voice acceptance run on Windows is usually the cloud media path below.

## Live Voice and Browser Demo Locally

For the Saleshandy public demo flow:

1. Seed the workspaces.
2. Enable voice.
3. Start the stack.
4. Open the meeting URL.

Recommended guide:

- [saleshandy-live.md](/c:/Users/Lenovo/OneDrive/Desktop/demobase/docs/acceptance/saleshandy-live.md)

Default live meeting URL:

- `http://localhost:3000/meet/demo-saleshandy-001`

## Deploy on Cloud

There is no single hard-coded cloud target in this repo. The practical deployment shape is:

1. Deploy `backend/` as a Python service using [`backend/Dockerfile`](/c:/Users/Lenovo/OneDrive/Desktop/demobase/backend/Dockerfile).
2. Deploy `frontend/` as a Next.js service using [`frontend/Dockerfile`](/c:/Users/Lenovo/OneDrive/Desktop/demobase/frontend/Dockerfile).
3. Run `stagehand-bridge/` as a separate Node service.
4. Use LiveKit Cloud or a reachable LiveKit server.
5. Run Qdrant as a managed service or a separate container.
6. Store `.env` values in your platform secret manager.

Recommended cloud topology:

- frontend on a public HTTPS domain
- backend on a private or public HTTPS API domain
- Stagehand bridge reachable only by backend if possible
- LiveKit Cloud for voice/browser media
- persistent volume for SQLite if you keep the MVP database

Minimum production env concerns:

- `FRONTEND_URL` must match the buyer-facing domain
- `BACKEND_URL` must match the public API origin
- `LIVEKIT_URL` should be `wss://...`
- `STAGEHAND_BRIDGE_URL` must resolve from the backend container
- `PLAYWRIGHT_HEADLESS=true`
- `ENABLE_STAGEHAND=true` for live browser automation
- `ENABLE_VOICE=true` for voice demos

If you want the repo's Windows helper for a cloud-backed local run with LiveKit Cloud, use:

- [livekit-cloud.md](/c:/Users/Lenovo/OneDrive/Desktop/demobase/docs/acceptance/livekit-cloud.md)
- `npm run start:cloud`

## What To Take Care Of

Operational cautions:

- This repo uses SQLite by default. That is fine for local work and single-instance MVP use, but it is not the right long-term choice for high-concurrency cloud deployments.
- Keep `ENCRYPTION_KEY` stable across deploys or stored credentials will become unreadable.
- Voice requires microphone permission in the buyer browser.
- Remote browser video does not need special browser permission, but it does depend on LiveKit, the publisher path, and frontend track attachment all working together.
- On Windows, local Docker LiveKit can be less reliable than LiveKit Cloud for full realtime testing.
- Keep `PLAYWRIGHT_HEADLESS=false` during debugging when you need to inspect the server-side browser.
- Guardrails matter. Keep policies current for pricing, billing, destructive actions, and blocked routes.
- Do not expose sandbox credentials to the frontend.
- Make sure `allowed_domains` is tight for each workspace.

Product behavior expectations:

- the agent should show while telling
- walkthroughs should stay concrete and easy to follow
- pricing and other commercial questions should escalate
- the live stage should stay annotation-free

## How The Product Is Used

Admin workflow:

1. Create or seed a workspace.
2. Add docs, credentials, recipes, and policies.
3. Share the public token or direct URL.

Buyer workflow:

1. Open the public link.
2. Start the demo or meeting.
3. Ask questions in text or voice.
4. Watch the agent drive the product live.
5. End the session and review transcript or summary.

## Testing

Backend tests:

```powershell
cd backend
C:\Python313\python.exe -m pytest
```

Frontend unit tests:

```powershell
cd frontend
npm run test:unit
```

Frontend e2e:

```powershell
cd frontend
npm run test:e2e
```

Useful repo-level commands:

```powershell
npm run test
npm run coverage
npm run lint
npm run sanity
```

## Useful Runbooks

- [saleshandy-live.md](/c:/Users/Lenovo/OneDrive/Desktop/demobase/docs/acceptance/saleshandy-live.md)
- [livekit-cloud.md](/c:/Users/Lenovo/OneDrive/Desktop/demobase/docs/acceptance/livekit-cloud.md)
- [v2-architecture.md](/c:/Users/Lenovo/OneDrive/Desktop/demobase/docs/v2-architecture.md)
- [v3-rebuild.md](/c:/Users/Lenovo/OneDrive/Desktop/demobase/docs/v3-rebuild.md)

## Merge Notes

Before merging feature work into `main`, keep the repo clean:

- remove generated screenshots and `_artifacts/`
- do not commit logs
- do not commit `.env`
- run the targeted tests for the changed live flow

This repo is currently prepared around that workflow.
