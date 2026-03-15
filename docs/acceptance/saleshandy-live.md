# Saleshandy Live Demo Runbook

Use this runbook when you want the agent to drive the real Saleshandy public demo at `https://my.saleshandy.com/demo`.

## Prerequisites

1. Install backend dependencies:
   - `cd backend`
   - `C:/Python313/python.exe -m pip install -r requirements.txt`
2. Install frontend dependencies:
   - `cd frontend`
   - `npm install`
3. Choose one RTC path:
   - local Docker LiveKit: `npm run livekit:up`
   - recommended on Windows: use LiveKit Cloud instead and follow `docs/acceptance/livekit-cloud.md`
4. Seed the demo workspaces:
   - `npm run seed:acceptance`

## Start the stack

1. Backend:
   - `cd backend`
   - `set PLAYWRIGHT_HEADLESS=false`
   - `set ENABLE_VOICE=true`
   - `C:/Python313/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
2. Frontend:
   - `cd frontend`
   - `npm run dev`

## Saleshandy workspace

The seed script creates:
- workspace: `Saleshandy Live Demo`
- public token: `demo-saleshandy-001`
- auth mode: `none`
- allowed domains: `my.saleshandy.com`

Open:
- buyer demo: `http://localhost:3000/demo/demo-saleshandy-001`
- admin workspace: `http://localhost:3000/admin`

## Live demo flow

1. Click `Start Demo`.
2. Click `Start Live Demo`.
3. Wait for the browser view to connect.
4. Ask:
   - `Show me the sequence dashboard`
   - `Walk me through analytics reports`
   - `Can I get annual discount pricing?`
5. Use assist controls if needed:
   - `Pause`
   - `Resume`
   - `Next Step`
   - `Restart Demo`

## Expected behavior

- The browser boots through `https://my.saleshandy.com/demo` and lands inside the demo account.
- The agent can drive Sequences, Reports, CRM, and Unified Inbox recipes.
- Pricing or commercial questions escalate.
- Settings, billing, and admin routes are blocked.
- Session transcript and summary persist after ending the demo.

## Notes

- Voice requires local audio device access in the browser and the optional speech dependencies in `backend/requirements.txt`.
- For the first real run, keep `PLAYWRIGHT_HEADLESS=false` so you can observe the server-side browser if media transport fails.
- On Windows, local Docker LiveKit can fail during WebRTC peer connection. Prefer LiveKit Cloud for a realistic local acceptance run.
