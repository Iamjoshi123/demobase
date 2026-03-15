# LiveKit Cloud Setup

Use this path when you want to test the live browser + voice experience without relying on local Docker LiveKit on Windows.

## Required values

Get these from your LiveKit Cloud project:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

Expected Cloud URL shape:

- `wss://your-project.livekit.cloud`

## Local environment

Set these in your shell or `.env` before starting the app:

```powershell
$env:LIVEKIT_URL="wss://your-project.livekit.cloud"
$env:LIVEKIT_API_KEY="your-project-api-key"
$env:LIVEKIT_API_SECRET="your-project-api-secret"
```

## Start the app

From the repo root:

```powershell
npm run start:cloud
```

This starts:

- Stagehand bridge
- backend with Stagehand enabled
- backend voice enabled
- frontend dev server

It does not start local Docker LiveKit.

## Open the live meeting

Use:

- `http://127.0.0.1:3000/meet/demo-saleshandy-001`

Then:

1. click `Start Meeting`
2. click `Start Live Meeting`
3. allow microphone access
4. ask for:
   - analytics reports
   - CRM prospects
   - a blocked pricing question

## Expected result

- room join succeeds without the local Docker RTC failure
- microphone prompt appears
- transcript updates
- agent can respond
- browser walkthrough can attach to the live meeting
