# Agentic Demo Brain

AI-powered live product demo engine for B2B SaaS. A buyer opens a shareable link, talks to a voice AI agent, asks product questions, and watches the agent navigate a web app sandbox in real time.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Next.js UI  │───▶│  FastAPI API  │───▶│  SQLite / Qdrant │
│  (frontend)  │    │  (backend)   │    │  (storage)       │
└──────┬───────┘    └──────┬───────┘    └─────────────────┘
       │                   │
       │            ┌──────┴───────┐
       │            │  Services    │
       │            ├──────────────┤
       │            │ Retrieval    │  Qdrant + Docling
       │            │ Planner      │  Route to answer/demo/escalate
       │            │ Browser      │  Playwright automation
       │            │ Voice        │  LiveKit + faster-whisper
       │            │ Policies     │  Guardrails & audit
       │            │ Analytics    │  Session summaries
       │            └──────────────┘
       │
       └── Live browser viewport via screenshots/streaming
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional, for full stack)

### Option 1: Docker Compose

```bash
cp .env.example .env
# Edit .env with your settings
docker compose up
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option 2: Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m app.seed  # seed sample data
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Real Acceptance Scenario

The default seed script now loads a concrete buyer-demo workspace from `fixtures/acceptance/acme-crm-pro/`. Use that when you want to validate the product as a real workflow instead of as isolated APIs.

```bash
npm run seed:acceptance
npm run test:acceptance
```

Detailed manual runbook:

- `docs/acceptance/acme-crm-pro.md`

### Saleshandy Live Demo

The seed script also creates a `Saleshandy Live Demo` workspace for the public `https://my.saleshandy.com/demo` product flow. This workspace uses `browser_auth_mode=none`, so the live browser can start without sandbox credentials.

Local setup for the real-product path:

```bash
npm run livekit:up
npm run seed:acceptance
```

For Windows local testing, prefer LiveKit Cloud over Dockerized LiveKit for the real browser+voice path:

- `docs/acceptance/livekit-cloud.md`

One-command cloud start:

```bash
npm run start:cloud
```

Detailed runbook:

- `docs/acceptance/saleshandy-live.md`

### Make Commands

```bash
make dev          # Start both backend and frontend
make backend      # Start backend only
make frontend     # Start frontend only
make seed         # Seed sample data
make test         # Run tests
make lint         # Lint code
make docker-up    # Start via Docker Compose
make docker-down  # Stop Docker Compose
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application entry
│   │   ├── config.py         # Settings and env config
│   │   ├── database.py       # DB engine and session
│   │   ├── seed.py           # Sample data seeder
│   │   ├── models/           # SQLModel data models
│   │   ├── api/              # API route handlers
│   │   ├── services/         # Business logic
│   │   ├── browser/          # Playwright automation
│   │   ├── retrieval/        # Doc parsing + vector search
│   │   ├── voice/            # LiveKit voice sessions
│   │   ├── policies/         # Guardrails and policy engine
│   │   └── analytics/        # Session summaries + scoring
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js app router pages
│   │   ├── components/       # React components
│   │   ├── lib/              # API client and utilities
│   │   └── types/            # TypeScript interfaces
│   ├── package.json
│   └── tailwind.config.ts
├── fixtures/                 # Sample docs and screenshots
├── infra/                    # Docker configs
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Core Flows

1. **Admin Setup**: Create workspace, upload docs, add sandbox credentials, define demo recipes and policies.
2. **Buyer Demo**: Open shareable link, talk to AI agent via voice/text, watch live browser walkthrough.
3. **Analytics**: Session summary with questions asked, features shown, objections, and lead intent score.

## Configuration

All configuration is via environment variables. See `.env.example` for the full list.

### Model Strategy

- **Default**: Local models via Ollama (free, no API key needed)
- **Fallback**: OpenAI or Anthropic when env vars are set
- **Voice**: LiveKit Agents with faster-whisper for STT
- **Embeddings**: Local sentence-transformers, or OpenAI if key is set

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for the interactive OpenAPI documentation.

## Demo Recipes (Seeded)

1. Login and navigate to dashboard
2. Search for a record
3. Create a new record
4. Edit an existing record
5. Show reporting/analytics page

## Security & Guardrails

- Credentials stored encrypted (Fernet symmetric encryption)
- Never exposed to frontend
- Browser automation restricted to allowed domains/routes
- Policy middleware blocks: pricing negotiation, legal commitments, billing changes, unsupported features
- Full audit trail for every browser action
- Session-level isolation with credential locking

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic, SQLModel |
| Database | SQLite (MVP) |
| Vector Store | Qdrant |
| Doc Parsing | Docling |
| Browser | Playwright |
| Voice | LiveKit Agents, faster-whisper |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Infra | Docker, docker-compose |
