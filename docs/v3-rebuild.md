# V3 Rebuild Plan

## Product Scope

The product is a configured demo agent for web apps with:

- `product_url`
- optional simple demo credentials
- admin-provided docs/context
- admin-provided recipes for key flows
- policy boundaries

The buyer gets an embedded meeting launcher, joins a live meeting, asks product questions, and watches the agent drive the real product while explaining it.

This is **not** a generic autonomous web agent for arbitrary apps.

## Core Runtime Loop

Every buyer turn should run the same backend pipeline:

1. `intent`
2. `observe`
3. `retrieve`
4. `act`
5. `verify`
6. `narrate`

### Intent

Classify the buyer turn into one of:

- `answer_only`
- `show_and_tell`
- `clarify`
- `refuse`
- `escalate`

### Observe

Read the current product state from:

- current URL
- page title
- visible text
- Stagehand screen summary
- Stagehand action candidates

### Retrieve

Pull the most relevant admin-provided artifacts:

- docs
- seeded notes
- implementation details
- product vocabulary

### Act

Action priority:

1. Stagehand-first direct action
2. recipe fallback
3. answer only

### Verify

Never narrate from intent alone.

After every browser action, verify with page evidence:

- URL changed
- title changed
- target panel opened
- expected text appeared

### Narrate

Narration must come from verified state changes plus retrieved product context.

## Architecture Boundaries

### Keep

- `LiveKit` for room and media transport
- `Stagehand` for browser understanding/actions
- current workspace/session/recipe/policy models
- current admin flows until v3 parity

### Replace incrementally

- legacy live runtime logic
- generic browser narration
- mixed recipe-first behavior
- weak stage state handling in the buyer page

## New Backend Package

`backend/app/runtime_v3/`

Responsibilities:

- explicit turn pipeline
- Stagehand-first action planning
- verified browser narration helpers
- clean migration seam for v2 API/runtime

## Migration Strategy

1. build v3 runtime package beside legacy code
2. test v3 pipeline in isolation
3. swap v2 orchestrator onto v3 internals
4. swap live runtime action handling onto verified narration
5. remove dead legacy paths after parity

## GitHub Publishing

Do not publish the current repo state blindly.

Before pushing:

1. ignore logs, screenshots, coverage, and local artifacts
2. remove secrets from `.env`
3. keep legacy code in tree until v3 replacement is stable
4. create a clean commit series:
   - `docs: add v3 runtime plan`
   - `feat: add runtime_v3 scaffold`
   - `feat: verified browser narration`
   - `feat: migrate live voice to realtime`

