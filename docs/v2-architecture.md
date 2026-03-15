# Agentic Demo Brain V2

## Goal

Build a real agentic demo product where a buyer joins a meeting with the agent, asks questions in natural language, and gets a personalized walkthrough that combines:

- spoken conversation
- live browser navigation
- product knowledge retrieval
- policy-safe escalation and refusal

The v2 architecture avoids the screenshot-first path and treats the product as a real-time meeting system with a browser worker.

## Product surfaces

### 1. Meeting UI

Buyer-facing application for:
- joining a meeting
- publishing microphone audio
- seeing the shared browser session
- reading the transcript
- steering the conversation with text when needed

### 2. Admin UI

Configuration surface for:
- workspaces
- product docs
- policies
- recipes
- session review

The current admin UI is reusable. The buyer experience is not.

## Runtime services

### Meeting Orchestrator

Owns one buyer session and coordinates:
- buyer identity and meeting context
- conversation memory
- planner decisions
- browser goals
- agent replies
- escalation handoff

### Voice Pipeline

Owns:
- STT
- TTS
- real-time transport

The meeting UI should not own business logic. It only joins the room and renders media + events.

### Browser Worker

Owns:
- Playwright lifecycle
- authenticated or no-auth browser bootstrap
- page-state extraction
- recipe execution
- controlled exploratory actions
- browser media publishing

### Knowledge Layer

Owns:
- document retrieval
- citations
- structured product context
- page-state grounding

## Core session loop

1. Buyer joins meeting.
2. Orchestrator loads workspace, buyer profile, and goals.
3. Buyer asks a question.
4. Policy engine classifies the request.
5. Retriever and live page-state collectors gather context.
6. Planner decides:
   - answer
   - answer and demo
   - clarify
   - escalate
   - refuse
7. Browser worker executes the selected walkthrough when needed.
8. Agent speaks the response and updates transcript/state.

## Design boundaries

### Keep

- workspace and policy data concepts
- retrieval fallback behavior
- session analytics ideas
- admin CRUD patterns

### Replace

- screenshot-refresh live demo UX
- mixed browser/voice/session orchestration
- legacy live demo API flow
- direct coupling between planner and old demo routes

## V2 slice order

### Slice 1

Meeting domain and orchestration contract:
- new `/api/v2/meetings` routes
- meeting session models
- personalized text-turn orchestration
- explicit join and browser-plan contracts
- clean buyer meeting page

### Slice 2

Real RTC and browser worker:
- LiveKit meeting join
- browser worker attachment
- remote browser track
- voice pipeline

### Slice 3

Autonomous walkthrough quality:
- better page understanding
- adaptive exploratory navigation
- stronger personalization and multi-turn memory
- human handoff controls

## Non-goals for slice 1

- full production LiveKit session management
- full browser worker execution
- polished media UX
- arbitrary autonomous exploration

Slice 1 exists to establish a clean product contract and stop the old architecture from spreading.
