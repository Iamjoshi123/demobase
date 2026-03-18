# DemoAgent: Complete Product Specification
## Admin Console + Demo Stage — Production-Grade

---

## Part 0: Design Philosophy

Before any feature or flow, internalize these rules. Every screen, component, and interaction must pass through these filters.

### The Three Principles

**1. Earn every pixel.**
If an element doesn't directly help the user accomplish their current task, it doesn't exist. No decorative dividers. No "helpful" tooltips that nobody reads. No status badges that don't lead to an action. If you're debating whether something should be on the screen — it shouldn't.

**2. Text is the interface.**
Like Notion: the content IS the UI. Labels are clear enough to not need help text. Inputs are inline, not inside modals. Tables are readable without row striping or heavy borders. Typography hierarchy does the work that color and borders do in lesser products.

**3. Speed is a feature.**
Every page loads instantly or feels like it does. Optimistic updates everywhere — the UI responds before the server confirms. No loading modals. No multi-step wizards with "Next" buttons. One page, one scroll, everything saves automatically.

### Visual Language

```
Surfaces:     White (#FFFFFF) → Light gray (#F8F8F9) → Subtle gray (#F0F0F2)
Text:         Primary (#1A1A1A) → Secondary (#6B6B6E) → Tertiary (#A0A0A5)
Accent:       Single color. Warm amber (#D4963E). Used ONLY for: 
              primary CTAs, active states, the agent's visual identity.
Borders:      1px #E8E8EA. Used sparingly. Prefer spacing over lines.
Radius:       8px default. 12px for cards/containers. 20px for pills/tags.
Shadows:      Almost never. Only on elevated layers (dropdowns, command palette).
              When used: 0 4px 12px rgba(0,0,0,0.08)
Typography:   One sans-serif family. Two weights: Regular (400), Medium (500).
              Never bold. Never uppercase (except tiny labels if absolutely needed).
Spacing:      8px grid. Generous. Let things breathe.
Icons:        16px or 20px. Stroke-style only. Never filled. Never colored 
              (except active/selected states).
```

### Interaction Rules

- **No modals** for data entry. Modals only for destructive confirmations ("Delete this product?").
- **No wizards**. Multi-step processes happen on a single scrollable page with sections.
- **No dropdowns** when there are fewer than 6 options — use inline radio/toggle groups instead.
- **No toggle switches** for critical settings — too easy to accidentally flip. Use explicit radio buttons with labels.
- **Autosave everything.** Show a quiet "Saved" indicator that fades after 2 seconds. Never require a "Save" button.
- **Undo over confirm.** Instead of "Are you sure you want to delete?", delete immediately and show "Deleted. Undo" toast for 5 seconds.
- **Command palette (⌘K)** as the power-user navigation layer. Search across products, settings, sessions, knowledge entries.

---

## Part 1: Core Entities & Data Model

Before designing screens, understand what exists in the system.

### Entity Hierarchy

```
Organization (account)
└── Product (the SaaS being demoed)
    ├── Connection (how the agent accesses the product)
    ├── Knowledge (what the agent knows)
    │   ├── Source (a URL, video, file, or manual entry)
    │   └── Chunk (an individual piece of indexed knowledge)
    ├── Agent (how the agent behaves)
    │   ├── Persona (name, greeting, instructions)
    │   └── Rules (guardrails, escalation, response style)
    ├── Demo Config (session settings, suggested questions, post-session)
    └── Sessions (historical records of demo interactions)
        ├── Messages (conversation transcript)
        └── Events (navigation actions the agent took)
```

### Key Relationships

- One Organization → many Products
- One Product → one Connection (credentials/URL)
- One Product → many Sources → many Chunks
- One Product → one Agent config
- One Product → many Sessions
- One Session → many Messages + Events

### Product States

A product moves through four states:

```
[Draft] → [Configuring] → [Ready] → [Live]
```

- **Draft**: Created but no knowledge added yet.
- **Configuring**: At least one knowledge source added, but agent hasn't been tested.
- **Ready**: Agent tested, knowledge validated. Can go live.
- **Live**: Demo link is active. Prospects can access it.

The state is computed, not manually set. The UI shows what's missing to advance to the next state.

---

## Part 2: Information Architecture

### Navigation Structure

```
┌─ Sidebar (200px, collapsible) ─────────────────┐
│                                                  │
│  [Logo: DemoAgent]                               │
│                                                  │
│  Products                    ← default landing   │
│  Sessions                    ← cross-product     │
│                                                  │
│  ── separator ──                                 │
│                                                  │
│  Settings                                        │
│                                                  │
│  ── bottom ──                                    │
│  [Organization name]                             │
│  [User avatar + name]                            │
│                                                  │
└──────────────────────────────────────────────────┘
```

That's it. Three top-level items. Not five. Not seven. Three.

Why: Products is where 90% of the work happens. Sessions is the monitoring/review layer. Settings is account-level config. Everything else (knowledge, agent config, embed) lives WITHIN a product — not as top-level navigation.

### Inside a Product: Tab Navigation

When you click into a product, you see horizontal tabs (not more sidebar items):

```
[Product Name]                                    [Live ●]  [Share]

Overview    Knowledge    Agent    Sessions    Share
─────────────────────────────────────────────────────
```

Five tabs. Each is a single page, no sub-navigation needed.

---

## Part 3: Screens & Features — Detailed Specification

### Screen 1: Products List (`/products`)

**Purpose:** See all configured products at a glance. Create new ones.

**Layout:** Clean list — not a card grid. Each row is a product.

```
┌──────────────────────────────────────────────────────────┐
│  Products                                    [+ New]     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  🔵 Saleshandy              Live    142 sessions   │  │
│  │     saleshandy.com           ●      Last: 2h ago   │  │
│  ├────────────────────────────────────────────────────┤  │
│  │  ○ TrulyInbox               Draft   0 sessions     │  │
│  │     trulyinbox.com                  Created: Today  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Each row shows:**
- Product name (clickable → goes to product overview)
- URL (subdued text)
- State indicator (Draft / Configuring / Ready / Live)
- Session count (lifetime)
- Last activity timestamp

**Actions:**
- Click row → enter product
- [+ New] button → opens a NEW product inline (not a modal, not a new page)
  - Inline form appears at top of list: Product name + URL. That's it. Hit Enter to create.
  - The product is created in Draft state. User clicks into it to configure.

**Empty state:** Centered illustration + "Add your first product" + single CTA button. Brief one-sentence explanation: "A product is the SaaS application you want your AI agent to demo."

---

### Screen 2: Product Overview (`/products/[id]`)

**Purpose:** The product's home page. Shows setup completeness, key stats, and quick access to everything.

**Layout:** Single scrollable page with clear sections.

**Section A: Product Identity**
Inline-editable fields. No "Edit" button — just click the text and type.

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  Product name        Saleshandy                     ✎   │
│  Website             saleshandy.com                 ✎   │
│  Description         Cold email and sales engagement ✎   │
│                      platform for B2B outreach           │
│  Target audience     Sales teams, SDRs, agencies    ✎   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Fields:
- **Product name**: Text. Required.
- **Website URL**: URL. Required. Used as the base for agent navigation.
- **One-line description**: Text. Required. Max 120 characters. Becomes the agent's elevator pitch.
- **Target audience**: Text. Optional. Helps agent calibrate language.

**Section B: Setup Progress**
A quiet checklist — NOT a progress bar. Shows what's done and what's remaining.

```
┌──────────────────────────────────────────────────────────┐
│  Setup                                                   │
│                                                          │
│  ✓  Product details added                                │
│  ✓  Demo connection configured                           │
│  ✓  Knowledge base has 47 entries                        │
│  ○  Test your agent (recommended before going live)      │
│                                                          │
│  Status: Ready                          [Go Live]        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Each checklist item links to the relevant tab. "Go Live" generates the demo link and switches state to Live. If already live, this shows the active link and a "Pause" option.

**Section C: Demo Connection**
How the agent accesses the product. Collapsed by default if already configured.

```
┌──────────────────────────────────────────────────────────┐
│  Demo Connection                          [Test ▶]       │
│                                                          │
│  Access type                                             │
│  (●) Login with credentials                              │
│  ( ) Public URL (no login needed)                        │
│                                                          │
│  Login URL         app.saleshandy.com/login         ✎   │
│  Email             demo@saleshandy.com              ✎   │
│  Password          ••••••••••                       ✎   │
│  Start page        /sequences              (optional) ✎ │
│                                                          │
│  Connection status: ✓ Verified 3 hours ago               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Fields:
- **Access type**: Radio toggle. Two options. Determines which fields appear below.
- **Login URL**: URL. Where the agent goes to log in.
- **Email / Username**: Text. Credential field.
- **Password**: Password field. Stored encrypted. Show/hide toggle.
- **Start page**: Optional URL path. Where the agent lands after login (e.g., `/dashboard`). If blank, it stays wherever the login redirects.
- **[Test]** button: Initiates a real login attempt. Shows a mini live-view window (300x200px) so the admin can SEE the agent logging in. Results in ✓ Verified or ✗ Failed with error details.

For "Public URL" access type:
- Only one field: the product URL. No credentials needed.

**Restricted areas** (collapsed subsection under Demo Connection):
```
│  Restricted areas (optional)                             │
│                                                          │
│  Pages the agent should never visit:                     │
│  [/settings/billing                              ] [×]   │
│  [/admin                                         ] [×]   │
│  [+ Add URL pattern]                                     │
```

Simple list of URL patterns. The agent will not navigate to any URL matching these patterns.

**Section D: Quick Stats (only visible when Live)**

```
┌──────────────────────────────────────────────────────────┐
│  Last 30 days                                            │
│                                                          │
│  Sessions     Avg. Duration     Questions Asked          │
│  142          8m 24s            4.2 per session           │
│                                                          │
│  Top asked features                                      │
│  1. Email Sequences (38%)                                │
│  2. Lead Finder (22%)                                    │
│  3. Email Warmup (18%)                                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Three numbers + a ranked list of what prospects ask about most. That's it. No charts. No graphs. Numbers tell the story faster.

---

### Screen 3: Knowledge (`/products/[id]/knowledge`)

**Purpose:** Manage everything the agent knows. The most important screen after the demo itself.

**Layout:** Two-zone layout — source list on the left, content view on the right (like a mail client or Notion's database views).

```
┌──────────────────────────────────────────────────────────┐
│  Knowledge                            [+ Add source]     │
│                                                          │
│  Filter: [All ▾]  Search: [________________]    47 items │
│                                                          │
│  ┌─ Source List (40%) ────┐  ┌─ Content (60%) ────────┐  │
│  │                        │  │                         │  │
│  │  ● Help Center         │  │  Source: Help Center    │  │
│  │    23 entries           │  │  URL: help.saleshandy… │  │
│  │    Synced: 2h ago       │  │  Status: ✓ Synced      │  │
│  │                        │  │  Entries: 23            │  │
│  │  ● Walkthrough Video   │  │                         │  │
│  │    12 entries           │  │  ┌──────────────────┐  │  │
│  │    Processed            │  │  │ How to create a  │  │  │
│  │                        │  │  │ new sequence      │  │  │
│  │  ● Custom Entries       │  │  │ ───────────────  │  │  │
│  │    8 entries            │  │  │ To create a new  │  │  │
│  │    Manual               │  │  │ email sequence,  │  │  │
│  │                        │  │  │ navigate to...   │  │  │
│  │  ● Product PDF          │  │  │                  │  │  │
│  │    4 entries            │  │  │ Source: help...  │  │  │
│  │    Processed            │  │  └──────────────────┘  │  │
│  │                        │  │                         │  │
│  └────────────────────────┘  │  [Edit]  [Delete]       │  │
│                              └─────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Left panel: Source list**
Each source is a collapsible group. Shows:
- Source type icon (subtle, stroke-style)
- Source name/identifier
- Number of knowledge entries extracted
- Sync/processing status
- Click to expand → shows individual entries within that source

**Right panel: Content view**
When a source is selected, shows source metadata and its entries.
When an individual entry is selected, shows the full content with edit capability.

**[+ Add source] flows:**

Clicking "Add source" shows an inline selector (NOT a modal):

```
┌──────────────────────────────────────────────┐
│  What kind of knowledge?                     │
│                                              │
│  ◻ Web pages      Paste URLs to crawl        │
│  ◻ Video          Upload or paste link       │
│  ◻ File           PDF, DOCX, or text file    │
│  ◻ Write manually Q&A entries you write      │
│                                              │
└──────────────────────────────────────────────┘
```

**Flow: Web pages**
```
Step 1 (inline):
┌──────────────────────────────────────────────┐
│  Add web pages                               │
│                                              │
│  Paste URLs (one per line):                  │
│  ┌────────────────────────────────────────┐  │
│  │ https://help.saleshandy.com/sequences │  │
│  │ https://help.saleshandy.com/warmup    │  │
│  │ https://help.saleshandy.com/leads     │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ( ) Crawl these pages only                  │
│  (●) Crawl these + linked pages (1 level)    │
│                                              │
│  [Import]                                    │
│                                              │
└──────────────────────────────────────────────┘

Step 2 (processing state):
┌──────────────────────────────────────────────┐
│  Importing 3 URLs...                         │
│                                              │
│  ✓ /sequences — 8 entries extracted          │
│  ◌ /warmup — processing...                   │
│  ○ /leads — queued                           │
│                                              │
└──────────────────────────────────────────────┘

Step 3 (complete):
Source appears in the left panel. Entries are immediately 
searchable and available to the agent.
```

**Flow: Video**
```
┌──────────────────────────────────────────────┐
│  Add video                                   │
│                                              │
│  [Upload file]  or  paste URL:               │
│  ┌────────────────────────────────────────┐  │
│  │ https://youtube.com/watch?v=...       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [Process]                                   │
│                                              │
└──────────────────────────────────────────────┘

Processing shows:
┌──────────────────────────────────────────────┐
│  Processing video...                         │
│                                              │
│  ✓ Downloaded                                │
│  ✓ Transcribed (14:32 duration)              │
│  ◌ Chunking into knowledge entries...        │
│                                              │
└──────────────────────────────────────────────┘

Once done, entries appear with timestamps:
  [0:00–1:45]  Introduction to Saleshandy dashboard
  [1:45–4:12]  Creating an email sequence
  [4:12–6:30]  Setting up A/B test variants
  ...

Each entry is editable — admin can correct transcription 
errors or add context.
```

**Flow: File upload**
Drag-and-drop zone. Accepts PDF, DOCX, TXT, MD. Processes immediately. Shows extracted entries for review.

**Flow: Manual entry**
```
┌──────────────────────────────────────────────┐
│  Add knowledge entry                         │
│                                              │
│  Topic / Question:                           │
│  ┌────────────────────────────────────────┐  │
│  │ What makes Saleshandy different from  │  │
│  │ Apollo.io?                             │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Answer / Content:                           │
│  ┌────────────────────────────────────────┐  │
│  │ Unlike Apollo which focuses on being  │  │
│  │ a database-first tool, Saleshandy is  │  │
│  │ built for cold email execution. Key   │  │
│  │ differences: built-in email warmup,   │  │
│  │ unified inbox, sender rotation...     │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [Save entry]                                │
│                                              │
└──────────────────────────────────────────────┘
```

**Bulk knowledge features:**
- **Search**: Full-text search across all entries from all sources. Fast. Instant results as you type.
- **Filter by source**: Dropdown to show entries from specific sources only.
- **Edit inline**: Click any entry → edit content directly in the right panel. Autosaves.
- **Delete**: Select entries → delete. Undo toast.
- **Re-sync**: For URL sources, a "Re-sync" button re-crawls and updates entries. Shows diff of what changed.

**Test Agent (embedded in Knowledge tab):**

A persistent, collapsible panel at the bottom of the Knowledge screen:

```
┌──────────────────────────────────────────────────────────┐
│  ─── Test Agent ─────────────────────── [Expand ▲]       │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  You: How does email warmup work?                  │  │
│  │                                                    │  │
│  │  Agent: Email warmup gradually increases your      │  │
│  │  sending volume over time to build domain          │  │
│  │  reputation. Saleshandy's warmup connects to...    │  │
│  │                                                    │  │
│  │  Confidence: 92%                                   │  │
│  │  Sources used: Help Center → Email Warmup Guide    │  │
│  │                 Video → [4:12–6:30]                │  │
│  │                                                    │  │
│  │  ────────────────────────────────────────────────  │  │
│  │                                                    │  │
│  │  [Ask a question...                        ] [→]   │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

This is knowledge-only testing — the agent answers questions but doesn't navigate the browser. It shows confidence scores and which knowledge chunks were retrieved. This is how the admin validates that their knowledge base is working before going live.

Critical: every test response shows a "Sources used" section. If a response has low confidence or uses no sources, that's a signal to add more knowledge in that area. This feedback loop is the core quality mechanism.

---

### Screen 4: Agent (`/products/[id]/agent`)

**Purpose:** Configure how the agent behaves, speaks, and handles edge cases.

**Layout:** Single scrollable page. Three sections.

**Section A: Persona**

```
┌──────────────────────────────────────────────────────────┐
│  Persona                                                 │
│                                                          │
│  Agent name                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ (empty — agent won't introduce itself by name)     │  │
│  └────────────────────────────────────────────────────┘  │
│  Leave blank for a nameless guide. Set a name like       │
│  "Sarah" if you want a named persona.                    │
│                                                          │
│  Greeting message                                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Hey! I'm here to walk you through Saleshandy.     │  │
│  │ What would you like to explore?                    │  │
│  └────────────────────────────────────────────────────┘  │
│  First message the prospect sees. Keep it short.         │
│                                                          │
│  Tone                                                    │
│  How formal?       Casual  ○ ○ ● ○ ○  Formal            │
│  How technical?    Simple  ○ ● ○ ○ ○  Technical          │
│                                                          │
│  Custom instructions                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Always mention the 7-day free trial when relevant. │  │
│  │ If asked about competitors, focus on what we do    │  │
│  │ well rather than criticizing others.               │  │
│  │ Emphasize that we're built specifically for cold   │  │
│  │ email, not general CRM.                            │  │
│  └────────────────────────────────────────────────────┘  │
│  Freeform instructions that shape the agent's behavior.  │
│  Write as if you're briefing a new team member.          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Fields:
- **Agent name**: Text. Optional. If set, the agent uses it in greeting. If blank, the agent is a nameless guide.
- **Greeting message**: Textarea. Required. Max 280 characters. What the prospect sees first.
- **Tone — Formality**: 5-point radio scale. Casual ↔ Formal. Affects language register.
- **Tone — Technicality**: 5-point radio scale. Simple ↔ Technical. Affects jargon usage and explanation depth.
- **Custom instructions**: Textarea. Optional. Unlimited. Freeform text injected into the agent's system prompt. This is the power-user escape hatch for any behavioral nuance the structured fields don't cover.

Two sliders instead of three. Dropped "enthusiasm" — it's too subjective and hard to reliably control in an LLM. Formality and technicality are the two axes that actually change output meaningfully.

**Section B: Response Behavior**

```
┌──────────────────────────────────────────────────────────┐
│  Response Behavior                                       │
│                                                          │
│  Answer length                                           │
│  (●) Concise — 2-3 sentences, let the demo do the       │
│      talking                                             │
│  ( ) Balanced — short paragraphs with key details        │
│  ( ) Detailed — thorough explanations with context       │
│                                                          │
│  When the agent doesn't know something                   │
│  (●) Acknowledge honestly and offer to connect with      │
│      your team                                           │
│  ( ) Acknowledge and move on (no escalation offer)       │
│  ( ) Try to answer from general knowledge (less safe)    │
│                                                          │
│  Show navigation in the product                          │
│  (●) Automatically — agent navigates to relevant         │
│      features while explaining                           │
│  ( ) Only when asked — agent explains verbally unless    │
│      the prospect says "show me"                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Three questions. Three radio groups. No toggles, no sliders, no complexity. Each option has a one-line description so the admin understands the tradeoff without needing documentation.

**Section C: Guardrails & Escalation**

```
┌──────────────────────────────────────────────────────────┐
│  Guardrails                                              │
│                                                          │
│  Topics to deflect                                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Custom enterprise pricing                     [×] │  │
│  │ Upcoming features / product roadmap            [×] │  │
│  │ Internal company information                   [×] │  │
│  │                                                    │  │
│  │ [+ Add topic]                                      │  │
│  └────────────────────────────────────────────────────┘  │
│  When a prospect asks about these, the agent will        │
│  acknowledge the question and offer to connect them      │
│  with your team instead.                                 │
│                                                          │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  Escalation                                              │
│                                                          │
│  When the agent needs to hand off to a human:            │
│                                                          │
│  Booking link (Calendly, Cal.com, etc.)                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ https://calendly.com/saleshandy/demo              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Team email                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ sales@saleshandy.com                              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Escalation message                                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Great question — I want to make sure you get the  │  │
│  │ best answer. Let me connect you with the team.    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Fields:
- **Topics to deflect**: Editable tag-style list. Freeform text entries.
- **Booking link**: URL. Optional. If set, the agent shows a "Book a call" button during escalation.
- **Team email**: Email. Optional. If set, shown as an alternative contact method.
- **Escalation message**: Textarea. The agent's handoff message. Has a sensible default.

If BOTH booking link and email are empty, the agent simply acknowledges what it doesn't know and moves on — no dead-end CTA pointing nowhere.

---

### Screen 5: Sessions (`/products/[id]/sessions` AND `/sessions`)

**Purpose:** Review what happened in demo sessions. Identify patterns.

Two access points — same data:
- `/sessions` shows ALL sessions across ALL products (global view)
- `/products/[id]/sessions` shows sessions for ONE product (filtered view)

**Layout:** Clean table. Airtable-style.

```
┌──────────────────────────────────────────────────────────┐
│  Sessions                                                │
│                                                          │
│  Filter: [All products ▾]  [Last 30 days ▾]  [Search]   │
│                                                          │
│  Date          Product      Duration  Questions  Handoff │
│  ─────────────────────────────────────────────────────── │
│  Mar 15, 2:40p Saleshandy   12:34     6          No     │
│  Mar 15, 11:02 Saleshandy   4:12      2          Yes    │
│  Mar 14, 9:15a Saleshandy   18:45     11         Yes    │
│  Mar 13, 4:30p Saleshandy   6:02      3          No     │
│                                                          │
│  Showing 4 of 142 sessions              [Load more]      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Columns:
- **Date**: Timestamp, human-readable format
- **Product**: Product name (relevant in global view)
- **Duration**: Session length in mm:ss
- **Questions**: Number of questions the prospect asked
- **Handoff**: Whether escalation was triggered (Yes/No)

Click a row → opens session detail.

**Session Detail (`/sessions/[id]`)**

```
┌──────────────────────────────────────────────────────────┐
│  ← Back to sessions                                      │
│                                                          │
│  Session — Mar 15, 2026, 2:40 PM                         │
│  Product: Saleshandy · Duration: 12:34 · 6 questions     │
│                                                          │
│  ┌─ Transcript ──────────────────────────────────────┐   │
│  │                                                    │   │
│  │  2:40:00  Agent                                    │   │
│  │  Hey! I'm here to walk you through Saleshandy.    │   │
│  │  What would you like to explore?                   │   │
│  │                                                    │   │
│  │  2:40:15  Prospect                                 │   │
│  │  How do I set up email sequences?                  │   │
│  │                                                    │   │
│  │  2:40:18  Agent                                    │   │
│  │  Let me show you the sequence builder.             │   │
│  │  → Navigated to /sequences                         │   │
│  │  → Clicked "Create Sequence"                       │   │
│  │                                                    │   │
│  │  2:40:22  Agent                                    │   │
│  │  This is where you create multi-step outreach      │   │
│  │  campaigns. You can add email steps, set delays    │   │
│  │  between them, and create A/B variants...          │   │
│  │                                                    │   │
│  │  Sources: Help Center → Sequences Guide (92%)      │   │
│  │                                                    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Insights ────────────────────────────────────────┐   │
│  │  Features explored: Sequences, Warmup, Lead Finder │  │
│  │  Unanswered questions: 1                           │  │
│  │    "Do you integrate with Pipedrive?"              │  │
│  │  Handoff triggered: No                             │  │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

The transcript is the primary content. It shows:
- Timestamps for each message
- Agent messages with source attribution (which knowledge chunks were used)
- Prospect messages
- Agent navigation events (inline, styled differently — as system events, not messages)

Below the transcript, an "Insights" summary panel:
- Features explored (automatically tagged from navigation events)
- Unanswered questions (questions where confidence was low or agent deflected)
- Whether handoff was triggered

The "Unanswered questions" section is the most actionable — it directly tells the admin what knowledge gaps to fill. Clicking an unanswered question → navigates to Knowledge tab with that question pre-filled as a new custom entry.

---

### Screen 6: Share (`/products/[id]/share`)

**Purpose:** Get the demo link. Configure what prospects see when they arrive.

**Layout:** Simple, focused page.

```
┌──────────────────────────────────────────────────────────┐
│  Share                                                   │
│                                                          │
│  ┌─ Demo Link ───────────────────────────────────────┐   │
│  │                                                    │   │
│  │  https://demo.yourdomain.com/s/sh-abc123          │   │
│  │                                        [Copy]      │   │
│  │                                                    │   │
│  │  Status: Live ●                       [Pause]      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Starter Questions ───────────────────────────────┐   │
│  │                                                    │   │
│  │  Shown as clickable suggestions in the demo:       │   │
│  │                                                    │   │
│  │  1. How do email sequences work?              [×]  │   │
│  │  2. Show me the lead finder                   [×]  │   │
│  │  3. How does email warmup help deliverability? [×] │   │
│  │  4. What integrations do you support?         [×]  │   │
│  │  5. Can I see the analytics dashboard?        [×]  │   │
│  │                                                    │   │
│  │  [+ Add question]                                  │   │
│  │                                                    │   │
│  │  Show ___3___ questions at a time                  │   │
│  │  Rotate based on conversation context              │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Session Settings ────────────────────────────────┐   │
│  │                                                    │   │
│  │  Session time limit                                │   │
│  │  ( ) 10 minutes                                    │   │
│  │  (●) 20 minutes                                    │   │
│  │  ( ) 30 minutes                                    │   │
│  │  ( ) No limit                                      │   │
│  │                                                    │   │
│  │  When session ends                                 │   │
│  │  (●) Show summary with call-to-action              │   │
│  │  ( ) Redirect to a URL                             │   │
│  │                                                    │   │
│  │  CTA button text    [Book a live demo         ]    │   │
│  │  CTA link           [https://calendly.com/... ]    │   │
│  │                                                    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Appearance ──────────────────────────────────────┐   │
│  │                                                    │   │
│  │  Logo          [Upload]  or  ← current logo        │   │
│  │  Accent color  [■ #D4963E]  ← click to change      │   │
│  │                                                    │   │
│  │  Preview                    [Open preview ↗]       │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Everything the prospect experiences is configured here:
- **Demo link**: The shareable URL. Copy button. Pause/resume toggle.
- **Starter questions**: The clickable suggestion pills shown in the demo. Ordered list, draggable to reorder. Admin controls how many show at once.
- **Session settings**: Time limit, end behavior, CTA configuration.
- **Appearance**: Logo and accent color override. Plus a "Preview" button that opens the demo stage exactly as a prospect would see it.

---

### Screen 7: Settings (`/settings`)

**Purpose:** Account-level configuration. Minimal.

```
┌──────────────────────────────────────────────────────────┐
│  Settings                                                │
│                                                          │
│  ┌─ Account ─────────────────────────────────────────┐   │
│  │  Organization name    Saleshandy Inc.         ✎   │   │
│  │  Owner email          malav@saleshandy.com    ✎   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ API ─────────────────────────────────────────────┐   │
│  │  API Key              sk-••••••••••••••4f2a        │   │
│  │                       [Regenerate]  [Copy]         │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Billing ─────────────────────────────────────────┐   │
│  │  Current plan: Free (POC)                          │   │
│  │  Sessions this month: 12 / 50                      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Danger Zone ─────────────────────────────────────┐   │
│  │  [Delete account]                                  │   │
│  └────────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Part 4: Demo Stage (Prospect Side) — Detailed Spec

This was covered in the earlier frontend prompt but here are the production-grade additions:

### Pre-Session Loading

When a prospect clicks the demo link, they see:

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│                                                          │
│              [Product Logo]                               │
│                                                          │
│              Preparing your demo...                       │
│              ═══════════════════ (shimmer line)           │
│                                                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

The system is:
1. Spinning up a browser session (Browserbase)
2. Logging into the demo account
3. Navigating to the start page
4. Initializing the conversation

This takes 3-8 seconds. The loading screen is calm, branded with the product logo, and uses the shimmer line (not a spinner).

If loading fails (credentials expired, Browserbase down):
```
│  Something went wrong while setting up the demo.         │
│  This usually resolves itself in a few minutes.          │
│                                                          │
│  [Try again]    or    [Contact the team →]               │
```

### During Session

The live demo experience as specified in the frontend prompt. Adding specifics:

**Context bar behavior:**
- Hidden by default
- Appears when agent starts navigating: `Viewing: Sequences → Create New`
- Updates as the agent moves through the product
- Has subtle breadcrumb-style formatting
- Fades out after 3 seconds of no navigation

**Agent behavior during navigation:**
- When the agent navigates, it sends TWO things simultaneously:
  1. A text message to the conversation (the explanation)
  2. Browser actions to the demo screen (the visual)
- The prospect sees the product changing while reading the explanation
- Navigation actions appear as subtle inline events in the conversation:
  `→ Opening Sequences` (styled in --text-tertiary, not as a full message)

**Suggested questions behavior:**
- Show 3 questions below the input at all times
- After each agent response, the suggestions update contextually
- If the agent just showed email sequences, suggestions might be:
  `[How does A/B testing work?]  [Show me analytics]  [What about follow-ups?]`
- Suggestions are NOT the same as the admin's starter questions — the starter questions appear ONLY at the beginning. Subsequent suggestions are generated by the AI based on context.

**Session time warning:**
- At 2 minutes before time limit: The agent naturally mentions "We have a couple more minutes — any final things you'd like to see?"
- At time limit: The agent wraps up gracefully and the UI transitions to the post-session page
- The prospect is NEVER abruptly cut off

### Post-Session

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│              [Product Logo]                               │
│                                                          │
│              Thanks for exploring Saleshandy!             │
│                                                          │
│              During this session, we covered:             │
│              · Email Sequences                            │
│              · Lead Finder                                │
│              · Email Warmup                               │
│                                                          │
│              ┌────────────────────────┐                   │
│              │  Book a live demo  →   │                   │
│              └────────────────────────┘                   │
│                                                          │
│              or start a free trial at saleshandy.com      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Simple. Logo, summary of features covered (auto-generated from navigation events), CTA button (configured by admin in Share settings), and a secondary text link.

---

## Part 5: User Flows (End-to-End Journeys)

### Flow 1: First-Time Setup (Admin)

```
Sign up / Log in
    ↓
Land on Products page (empty state)
    ↓
Click "Add your first product"
    ↓
Enter product name + URL → product created in Draft
    ↓
Redirected to Product Overview
    ↓
Fill in description + target audience (inline editing)
    ↓
Configure Demo Connection (enter credentials, test login)
    ↓
Go to Knowledge tab → Add first source (help center URLs)
    ↓
Wait for processing → Review extracted entries
    ↓
Open Test Agent panel → Ask 5-10 questions → Verify quality
    ↓
Go to Agent tab → Customize greeting + tone (optional)
    ↓
Go to Share tab → Configure starter questions + session settings
    ↓
Click "Go Live" on Overview → Demo link generated
    ↓
Copy link → Share with first prospect
```

Total estimated time: 20-30 minutes for initial setup.

### Flow 2: Ongoing Knowledge Maintenance (Admin)

```
Review Sessions → Find unanswered questions
    ↓
Click unanswered question → Taken to Knowledge tab 
with question pre-filled as new entry
    ↓
Write answer → Save
    ↓
Test Agent → Verify the new entry works
    ↓
Done — agent is immediately smarter
```

This is the core improvement loop. Every session that exposes a gap becomes an improvement opportunity.

### Flow 3: Prospect Experience

```
Receive demo link (email, website, sales outreach)
    ↓
Click link → Loading screen (3-8 seconds)
    ↓
Demo stage loads: Browser stream + Conversation panel
    ↓
Agent greets with configured message
    ↓
Prospect sees starter questions as clickable pills
    ↓
Prospect clicks a question OR types their own
    ↓
Agent responds with text + navigates the product live
    ↓
Prospect watches, asks follow-ups
    ↓
If agent can't answer → Escalation message + CTA
    ↓
Session time warning at 2 minutes remaining
    ↓
Session ends → Post-session page with summary + CTA
```

### Flow 4: Agent can't answer → Knowledge gap → Fix

```
During session: Prospect asks something agent doesn't know
    ↓
Agent responds: "I don't have detailed info on that. 
Let me connect you with the team." + Shows booking CTA
    ↓
Session ends. Session is logged with "unanswered question" flag.
    ↓
Admin reviews sessions → Sees unanswered question
    ↓
Admin adds knowledge entry for that topic
    ↓
Next prospect who asks the same question → Agent answers correctly
```

---

## Part 6: Edge Cases & Error Handling

### Demo Connection Failures
- **Credentials expired**: Agent detects login failure → Shows prospect a graceful message: "The demo environment is being updated. Please try again in a few minutes." → Admin receives email notification: "Your demo credentials for [Product] may have expired."
- **Product is down**: Same graceful message to prospect. Admin notification.
- **Slow loading**: If browser session takes >10 seconds, show additional message: "This is taking a moment — hang tight."

### Agent Edge Cases
- **Prospect asks the same question twice**: Agent recognizes the repeat and offers to go deeper: "We touched on this earlier — would you like me to show you a different aspect of it?"
- **Prospect goes off-topic** (asks about weather, tells jokes): Agent briefly acknowledges and redirects: "Ha! I'm best at talking about [Product] though. What feature would you like to explore?"
- **Prospect is silent for >2 minutes**: Agent gently prompts: "Still there? I'm happy to show you around [popular feature] if you'd like."
- **Prospect asks about a competitor**: Agent uses knowledge base for competitive positioning if available. If not, stays neutral: "I'm best equipped to show you what [Product] does well. Want me to walk you through [relevant feature]?"
- **Multiple rapid questions**: Agent acknowledges the queue: "Great questions — let me tackle them one at a time." Answers in order.

### Admin Edge Cases
- **Deleting a product that's live**: Confirmation dialog (one of the rare cases we use a modal): "This product has an active demo link. Deleting it will immediately disable all demo sessions. Are you sure?"
- **No knowledge added but trying to go live**: Setup checklist blocks "Go Live" with clear message: "Add at least one knowledge source before going live."
- **Video transcription fails**: Show error with retry option. Common reason: unsupported format or too large. Show accepted formats and size limits.

---

## Part 7: What NOT to Build (POC Scope Boundaries)

Explicitly excluded from POC to keep scope tight:

- **Multi-user / team features**: One admin per organization. No roles, no permissions.
- **Widget / embed mode**: Only shareable link mode. No JavaScript widget for embedding on third-party sites.
- **Custom domains**: All demo links use our domain.
- **Session recording / replay**: Store transcripts only. No video replay of the browser session.
- **Analytics dashboard with charts**: Just the three numbers on the product overview. No trends, no time-series, no charts.
- **Billing / payments**: Placeholder page only. No Stripe integration.
- **Email notifications**: No automated emails to admin (session summaries, credential expiry alerts). Just the web UI.
- **A/B testing agent configs**: One agent config per product. No variant testing.
- **Prospect identification**: Sessions are anonymous. No asking for name/email before the demo.
- **Voice input/output**: Text only. Voice is a post-POC feature.
- **Agent "Guide me" mode**: View-only for the prospect. No handing over browser control.
- **Auto-generated knowledge from crawling**: Manual URL input only. No "crawl my entire site" feature.
- **Real-time collaboration**: No "watch a prospect's session live from admin."

These are all valid features for V2/V3. Listing them here ensures nobody accidentally builds them into the POC.

# DemoAgent: Revised Sidebar & Analytics Spec
## Addendum to Complete Product Spec

---

## Revised Sidebar Architecture

### The Problem with the Previous Approach

Three items in a sidebar screams "weekend project." A real SaaS platform has navigational depth because it does real things. But depth doesn't mean clutter — Linear has a rich sidebar and still feels clean. The trick is hierarchy and progressive disclosure.

### Sidebar Structure

```
┌─ Sidebar (240px) ──────────────────────────┐
│                                             │
│  [DemoAgent logo]                    [⌘K]  │
│                                             │
│  ─── WORKSPACE ───                          │
│                                             │
│  ◈  Dashboard                               │
│  ◱  Products                                │
│  ▤  Sessions                                │
│  ◎  Contacts                                │
│                                             │
│  ─── INTELLIGENCE ───                       │
│                                             │
│  △  Analytics                               │
│  ☰  Keywords & Topics                       │
│  ◉  Intent Signals                          │
│                                             │
│  ─── CONFIGURE ───                          │
│                                             │
│  ⚙  Settings                                │
│  ◇  Integrations                            │
│  ?  Help                                    │
│                                             │
│  ─── ─── ─── ─── ───                       │
│                                             │
│  ┌─ Product Switcher ───────────────────┐   │
│  │  ● Saleshandy                    ▾   │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  [User avatar]  Malav              ⚙       │
│                                             │
└─────────────────────────────────────────────┘
```

### Sidebar Behavior

**Three sections with clear purpose:**

**WORKSPACE** — where you do things. Day-to-day operations.
- **Dashboard**: Overview of what's happening across the platform. The home screen.
- **Products**: Configure the products being demoed. CRUD + setup.
- **Sessions**: Review individual demo sessions. The transcript/detail view.
- **Contacts**: Prospects who've engaged with demos. Even if anonymous, each session represents a prospect interaction worth tracking.

**INTELLIGENCE** — where you learn things. Data-driven insights.
- **Analytics**: The detailed metrics dashboard. Numbers, trends, breakdowns.
- **Keywords & Topics**: What prospects talk about. Frequency analysis of questions and themes.
- **Intent Signals**: Sentiment and buying intent analysis from conversations.

**CONFIGURE** — where you set things up. One-time or occasional.
- **Settings**: Organization, billing, API keys, team (future).
- **Integrations**: CRM connections, webhook configs, Slack notifications (future, but the nav item exists).
- **Help**: Docs link, support, changelog.

**Product Switcher:**
At the bottom of the sidebar, a persistent product context selector. Since all Intelligence data and Sessions are viewed through the lens of a specific product, the admin selects which product they're looking at here. This filters the entire dashboard, analytics, sessions, etc.

When the org has only one product, the switcher is visible but not emphasized. When multiple products exist, it becomes more prominent with a dropdown.

**Collapse behavior:**
- Full sidebar: 240px with labels
- Collapsed: 56px with icons only
- Toggle: Click the logo area or use keyboard shortcut
- On screens < 1024px: Auto-collapse to icon-only
- On screens < 768px: Hidden entirely, accessible via hamburger

**Active state:**
- Active nav item: Background tint using accent color at 8% opacity, with 2px left border in accent color
- Hover: Background tint at 4% opacity
- Section labels: Uppercase, --text-xs, --text-tertiary, letter-spacing 0.05em

**Design details:**
- Icons: 18px, stroke-style, 1.5px stroke weight. Monochrome (--text-secondary). Active: --text-primary.
- Font: --text-sm (13px) for nav items. --text-xs (11px) for section labels.
- Spacing: 4px between items within a section. 16px between sections.
- Divider between sections: Not a visible line — just spacing. The section label acts as the divider.
- The sidebar background is --bg-secondary (#F8F8F9 in light mode, #141416 in dark mode). Slightly different from the main content area to create depth without shadows.

---

## Revised Dashboard (`/dashboard`)

### Philosophy

The dashboard answers three questions every time the admin opens it:
1. **What happened?** — Recent activity and volume.
2. **What's working?** — Positive signals and engagement patterns.
3. **What needs attention?** — Gaps, drop-offs, unanswered questions.

It does NOT try to be a full analytics suite (that's the Analytics page). It's the morning briefing — scan it in 30 seconds, know where you stand.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Good afternoon, Malav                          Saleshandy ▾     │
│  Here's how your demos are performing.                           │
│                                                                  │
│  ┌─ Key Metrics (4 cards, single row) ──────────────────────┐    │
│  │                                                          │    │
│  │  Total Sessions    Avg Duration    Completion     Handoff │   │
│  │  ┌──────────┐     ┌──────────┐    ┌──────────┐   ┌─────┐│   │
│  │  │   142    │     │  8m 24s  │    │   74%    │   │ 18% ││   │
│  │  │ +23% ▲   │     │ +1m 12s ▲│    │ -3% ▼   │   │ +5% ▲││  │
│  │  │ vs last  │     │ vs last  │    │ vs last  │   │vs la ││  │
│  │  │ 30 days  │     │ 30 days  │    │ 30 days  │   │30 d  ││  │
│  │  └──────────┘     └──────────┘    └──────────┘   └─────┘│   │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ Session Volume (60%) ──────┐  ┌─ Engagement (40%) ───────┐  │
│  │                             │  │                           │  │
│  │  Sessions over time         │  │  Avg questions per session│  │
│  │                             │  │                           │  │
│  │  ┃     ┃┃                   │  │  4.2 questions            │  │
│  │  ┃   ┃ ┃┃ ┃                 │  │  ═══════════ 84%          │  │
│  │  ┃ ┃ ┃ ┃┃ ┃                 │  │  (vs 3.1 industry avg)   │  │
│  │  ┃ ┃ ┃ ┃┃ ┃ ┃              │  │                           │  │
│  │  ┃ ┃ ┃ ┃┃ ┃ ┃ ┃            │  │  Avg time to first       │  │
│  │  ──────────────── ──        │  │  question                │  │
│  │  Mon  Wed  Fri  Sun         │  │  12 seconds              │  │
│  │                             │  │                           │  │
│  │  [Last 7 days ▾]           │  │  Session completion rate  │  │
│  │                             │  │  74% finish full session  │  │
│  └─────────────────────────────┘  │  18% leave in first 2min │  │
│                                   │  8% hit time limit        │  │
│                                   └───────────────────────────┘  │
│                                                                  │
│  ┌─ Top Explored Features ─────┐  ┌─ Attention Needed ────────┐ │
│  │                             │  │                            │ │
│  │  Feature        Sessions %  │  │  Unanswered questions (7)  │ │
│  │  ─────────────────────────  │  │                            │ │
│  │  Email Sequences   38%  ██  │  │  "Do you integrate with    │ │
│  │  Lead Finder       22%  █▌  │  │   Pipedrive?"              │ │
│  │  Email Warmup      18%  █▎  │  │   Asked 4 times   [+ Add] │ │
│  │  Unified Inbox     12%  █   │  │                            │ │
│  │  Analytics          7%  ▌   │  │  "What's the API rate      │ │
│  │  Integrations       3%  ▏   │  │   limit?"                  │ │
│  │                             │  │   Asked 2 times   [+ Add] │ │
│  │                             │  │                            │ │
│  │                             │  │  "Can I white-label the    │ │
│  │                             │  │   reports?"                │ │
│  │                             │  │   Asked 2 times   [+ Add] │ │
│  │                             │  │                            │ │
│  └─────────────────────────────┘  │  [View all →]              │ │
│                                   └────────────────────────────┘ │
│                                                                  │
│  ┌─ Recent Sessions ────────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Date          Duration  Questions  Intent    Handoff    │    │
│  │  ─────────────────────────────────────────────────────── │    │
│  │  Today, 2:40p  12:34     6          Positive  No        │    │
│  │  Today, 11:02  4:12      2          Neutral   Yes       │    │
│  │  Yesterday     18:45     11         Positive  Yes       │    │
│  │  Mar 13        6:02      3          Negative  No        │    │
│  │  Mar 12        9:18      5          Positive  No        │    │
│  │                                                          │    │
│  │  [View all sessions →]                                   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Dashboard Components — Detailed

**Row 1: Key Metric Cards**

Four cards in a single row. Each card shows:
- Metric name (--text-sm, --text-secondary)
- Value (--text-2xl, --text-primary, medium weight)
- Trend vs previous period (+/-%, with subtle up/down arrow)
- Trend color: Green for positive trends, red for negative (using semantic colors, NOT the brand amber)

The four metrics:

| Metric | Definition | Why it matters |
|--------|-----------|---------------|
| **Total Sessions** | Number of demo sessions in selected period | Volume indicator. Is anyone using your demo? |
| **Avg Duration** | Mean session length | Engagement proxy. Longer = more interested. Under 2 minutes = something's wrong. |
| **Completion Rate** | % of sessions where prospect reached natural end (vs abandoned) | Quality indicator. High abandonment = poor first impression or agent failure. |
| **Handoff Rate** | % of sessions where escalation was triggered | Lead generation indicator. Handoffs are GOOD — it means the prospect wanted more. |

Period selector: Default "Last 30 days." Options: Last 7 days, Last 30 days, Last 90 days, All time. Single dropdown in the header area, affects ALL dashboard cards.

**Row 2: Session Volume + Engagement**

**Left (60%): Session Volume Chart**
- Simple bar chart. One bar per day (or per week for 90-day view).
- Bars in accent color at 60% opacity. Hover: full opacity + tooltip with exact count.
- X-axis: Date labels (abbreviated). Y-axis: Session count (auto-scaled, no gridlines).
- No legend needed — it's one data series.
- Below chart: Period selector specific to this chart (Last 7 / 30 / 90 days).
- Chart style: Minimal. No background grid. No border. Bars have 4px radius on top. Thin 1px baseline.

**Right (40%): Engagement Metrics**
Not a chart — just three stacked metric blocks:

1. **Avg questions per session**: The number, a simple horizontal bar showing it relative to a benchmark (if available), and context text.
2. **Avg time to first question**: How quickly after joining does the prospect engage? Fast = the greeting/UX is working. Slow = the prospect is confused or the loading is too slow.
3. **Session completion breakdown**: Three-line breakdown:
   - X% finish the full session (good)
   - X% leave in first 2 minutes (bad — first impression problem)
   - X% hit the time limit (might need longer sessions)

**Row 3: Features + Attention Needed**

**Left: Top Explored Features**
- Ranked list of product features that prospects asked about or the agent navigated to.
- Each row: Feature name, percentage of sessions that explored it, and a minimal inline bar.
- The inline bars are accent color, proportional. No axis needed — it's a visual ranking, not a precise chart.
- Max 8 features shown. "Others" grouped at the bottom if needed.
- This data comes from tracking which product pages/sections the agent navigated to during sessions.

**Right: Attention Needed**
This is the most ACTIONABLE panel on the entire dashboard.
- Shows questions the agent couldn't answer, grouped and ranked by frequency.
- Each unanswered question shows:
  - The question text (paraphrased/grouped if multiple prospects asked similarly)
  - "Asked X times" — frequency indicator
  - **[+ Add]** button — ONE CLICK creates a new knowledge entry with this question pre-filled
- This panel directly connects "what's going wrong" to "how to fix it."
- Capped at 5 items. "View all →" link to a full page.

**Row 4: Recent Sessions**
- Last 5 sessions. Compact table.
- Columns: Date, Duration, Questions count, Intent (Positive/Neutral/Negative), Handoff (Yes/No)
- Intent is a computed field — derived from sentiment analysis of the prospect's messages (see Intent Signals section below).
- Intent display: Text label with subtle color indicator dot (green/gray/red).
- Click row → goes to session detail.
- "View all sessions →" link.

---

## Analytics Page (`/analytics`)

### Purpose
Deep-dive into demo performance. The dashboard gives you the 30-second scan; Analytics gives you the 10-minute deep investigation.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Analytics                    [Last 30 days ▾]  [Export CSV]     │
│                                                                  │
│  ┌─ VOLUME & TIMING ────────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Sessions over time                                      │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │  (area chart — sessions per day/week)            │    │    │
│  │  │  ▓▓▓▓▓▓░░▓▓▓▓▓▓▓▓▓░▓▓▓▓▓▓▓▓░░▓▓▓▓▓▓▓          │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                                                          │    │
│  │  ┌─ By Day of Week ────┐  ┌─ By Time of Day ────────┐   │    │
│  │  │ Mon  ████████ 24    │  │ 6am   ░░                │   │    │
│  │  │ Tue  ██████ 18      │  │ 9am   ██████            │   │    │
│  │  │ Wed  █████████ 28   │  │ 12pm  ████████████      │   │    │
│  │  │ Thu  ████████ 22    │  │ 3pm   █████████████     │   │    │
│  │  │ Fri  █████████ 26   │  │ 6pm   █████            │   │    │
│  │  │ Sat  ██ 6           │  │ 9pm   ███              │   │    │
│  │  │ Sun  █ 4            │  │ 12am  ░                 │   │    │
│  │  └─────────────────────┘  └─────────────────────────┘   │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ ENGAGEMENT DEPTH ───────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Session Duration Distribution                           │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │  0-2m  ████████ 18%  (likely drop-offs)         │    │    │
│  │  │  2-5m  █████████████ 26%                        │    │    │
│  │  │  5-10m ████████████████████ 34%  ← sweet spot   │    │    │
│  │  │  10-20m ████████ 16%                            │    │    │
│  │  │  20m+  ███ 6%                                   │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                                                          │    │
│  │  ┌─ Questions per Session ─┐  ┌─ Features per Session ┐ │    │
│  │  │ Distribution histogram  │  │ Distribution histogram │ │    │
│  │  │ 0  ██ 8%               │  │ 1   █████ 22%         │ │    │
│  │  │ 1-2  ████████ 24%     │  │ 2-3 █████████ 38%    │ │    │
│  │  │ 3-5  █████████████ 38%│  │ 4-5 ████████ 28%     │ │    │
│  │  │ 6-10 ██████ 22%       │  │ 6+  ███ 12%          │ │    │
│  │  │ 10+  ██ 8%            │  │                       │ │    │
│  │  └────────────────────────┘  └────────────────────────┘ │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ FEATURE INTEREST MAP ───────────────────────────────────┐    │
│  │                                                          │    │
│  │  Feature            Views    Avg Time    Questions  Sent.│    │
│  │  ────────────────────────────────────────────────────────│    │
│  │  Email Sequences    54       3m 12s      2.4       😊 82%│   │
│  │  Lead Finder        31       2m 45s      1.8       😊 76%│   │
│  │  Email Warmup       26       1m 58s      1.2       😐 64%│   │
│  │  Unified Inbox      17       1m 22s      0.8       😊 71%│   │
│  │  Analytics          10       0m 48s      0.4       😐 58%│   │
│  │  Integrations        5       0m 32s      1.6       😟 42%│   │
│  │                                                          │    │
│  │  Sort: [Views ▾]                                        │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ CONVERSION FUNNEL ──────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Link Clicked → Session Started → Engaged (>2min) →     │    │
│  │  Handoff Requested → (CTA Clicked)                       │    │
│  │                                                          │    │
│  │  ████████████████████████████████████████  100%  312     │    │
│  │  █████████████████████████████████         82%   256     │    │
│  │  ██████████████████████████                68%   212     │    │
│  │  █████████                                 22%    69     │    │
│  │  ████                                      11%    34     │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Analytics Sections — Detailed

**Section 1: Volume & Timing**

Three visualizations:

**Sessions over time** — Area chart (not bar). Soft fill at 10% accent opacity, with a 2px accent line on top. Shows daily sessions for 30-day view, weekly for 90-day. Hover shows exact count + date.

**By Day of Week** — Horizontal bar chart. Shows which days get the most demos. Helps the admin understand their prospect's behavior. If Tuesday and Wednesday dominate, maybe the sales team should send demo links early in the week.

**By Time of Day** — Horizontal bar chart. 4-hour buckets (6am-10am, 10am-2pm, etc.). Shows when prospects are most active. Timezone displayed based on admin's setting. Helps with scheduling live support alongside AI demos.

**Section 2: Engagement Depth**

**Session Duration Distribution** — Horizontal bars showing what percentage of sessions fall into each bucket. The "0-2 minute" bucket is annotated as "likely drop-offs" to flag a potential problem. The highest bucket is annotated as "sweet spot" with a subtle highlight.

**Questions per Session** — Distribution showing how interactive sessions are. Low question count might mean the agent is doing great (explaining proactively) OR that the prospect isn't engaged. Cross-reference with duration to distinguish.

**Features per Session** — How many different product areas does a typical prospect explore? If most sessions only touch 1-2 features, the agent might not be proactive enough about showing related features.

**Section 3: Feature Interest Map**

This is the power table. For each product feature the agent can demo:

| Column | Definition |
|--------|-----------|
| **Feature** | Product feature/section name (auto-detected from navigation) |
| **Views** | Number of sessions that explored this feature |
| **Avg Time Spent** | Average time the agent spent on this feature per session |
| **Questions** | Average number of prospect questions about this feature |
| **Sentiment** | Aggregate sentiment from prospect messages while discussing this feature. Emoji indicator + percentage positive. |

This table tells the admin: "Prospects love your sequence builder (high views, long time, positive sentiment) but your integrations page is confusing them (low time, negative sentiment, lots of questions)."

Sortable by any column. This is the Airtable-style interaction — click column header to sort.

**Section 4: Conversion Funnel**

Horizontal funnel visualization showing drop-off at each stage:

1. **Link Clicked** — Someone opened the demo link (100% baseline)
2. **Session Started** — Browser loaded and agent connected (drop-off here = technical issues)
3. **Engaged (>2min)** — Prospect stayed and interacted past 2 minutes (drop-off here = first impression problem)
4. **Handoff Requested** — Prospect triggered escalation to human (this is a GOOD conversion event)
5. **CTA Clicked** — Prospect clicked the booking/signup CTA on the post-session page

Each stage shows: bar width proportional to %, exact percentage, and absolute number.

The funnel is the most investor-friendly visual — it immediately communicates "this tool generates qualified leads." The drop-off between stages tells the admin where to focus.

---

## Keywords & Topics Page (`/keywords`)

### Purpose
Understand what language prospects use and what they're most curious about. This is goldmine data for product marketing, sales enablement, and product development.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Keywords & Topics                    [Last 30 days ▾]           │
│                                                                  │
│  ┌─ TOP KEYWORDS ───────────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Words and phrases prospects use most frequently:        │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │                                                  │    │    │
│  │  │  email warmup ●●●●●●●●●●  42                    │    │    │
│  │  │  sequences ●●●●●●●●● 38                         │    │    │
│  │  │  deliverability ●●●●●●●  31                     │    │    │
│  │  │  cold email ●●●●●●  27                          │    │    │
│  │  │  lead finder ●●●●●  24                          │    │    │
│  │  │  API ●●●●  18                                   │    │    │
│  │  │  pricing ●●●● 16                                │    │    │
│  │  │  integration ●●● 14                             │    │    │
│  │  │  A/B testing ●●● 12                             │    │    │
│  │  │  bounce rate ●● 9                               │    │    │
│  │  │  hubspot ●● 8                                   │    │    │
│  │  │  apollo ●● 7                                    │    │    │
│  │  │  white label ● 4                                │    │    │
│  │  │  zapier ● 3                                     │    │    │
│  │  │                                                  │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                                                          │    │
│  │  View: (●) Frequency list  ( ) Word cloud                │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ QUESTION THEMES ────────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Recurring question patterns grouped by theme:            │    │
│  │                                                          │    │
│  │  ┌─ How it works (34 questions) ──────────────────────┐  │    │
│  │  │  "How does email warmup work?" — 12 times          │  │    │
│  │  │  "How do sequences work?" — 8 times                │  │    │
│  │  │  "How does the lead finder work?" — 6 times        │  │    │
│  │  │  "How does sender rotation work?" — 4 times        │  │    │
│  │  │  + 4 more                                          │  │    │
│  │  └────────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  ┌─ Comparisons (18 questions) ───────────────────────┐  │    │
│  │  │  "How is this different from Apollo?" — 7 times    │  │    │
│  │  │  "Why not just use HubSpot?" — 4 times            │  │    │
│  │  │  "Compared to Outreach?" — 3 times                 │  │    │
│  │  │  + 4 more                                          │  │    │
│  │  └────────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  ┌─ Pricing & Plans (14 questions) ───────────────────┐  │    │
│  │  │  "What does it cost?" — 6 times                    │  │    │
│  │  │  "Is there a free trial?" — 4 times                │  │    │
│  │  │  "What's the difference between plans?" — 4 times  │  │    │
│  │  └────────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  ┌─ Technical & Integration (12 questions) ───────────┐  │    │
│  │  │  "Do you have an API?" — 5 times                   │  │    │
│  │  │  "Zapier integration?" — 3 times                   │  │    │
│  │  │  "Do you integrate with Pipedrive?" — 4 times      │  │    │
│  │  └────────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  ┌─ Can I / Does it (9 questions) ────────────────────┐  │    │
│  │  │  "Can I white-label reports?" — 4 times            │  │    │
│  │  │  "Can I import from CSV?" — 3 times                │  │    │
│  │  │  "Does it work with Gmail?" — 2 times              │  │    │
│  │  └────────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ COMPETITOR MENTIONS ────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Competitor        Mentions    Context                    │    │
│  │  ─────────────────────────────────────────────────────── │    │
│  │  Apollo.io         7          Comparison, switching       │    │
│  │  HubSpot           4          Alternative consideration   │    │
│  │  Outreach          3          Comparison                  │    │
│  │  Instantly         2          Currently using             │    │
│  │  Lemlist           2          Previously used             │    │
│  │                                                          │    │
│  │  Click a competitor to see exact conversation excerpts.   │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Keywords & Topics — Detailed

**Top Keywords:**
- Extracted from prospect messages using NLP (keyword extraction, not just word frequency — "email warmup" as a bigram, not "email" and "warmup" separately).
- Displayed as a ranked horizontal bar list (cleaner than word clouds, more precise).
- Optional toggle to word cloud view for visual exploration.
- Each keyword is clickable → shows the sessions where this keyword appeared.
- Competitor names automatically highlighted with a different color indicator.

**Question Themes:**
- Questions are clustered by AI into thematic groups.
- Each theme shows: theme name (auto-generated), total question count, and top individual questions with their frequency.
- Themes are collapsible. Top 3 expanded by default, rest collapsed.
- This is the most valuable view for product marketing — it literally tells you what your prospects care about, in their own words.

**Competitor Mentions:**
- Automatically detected when prospects mention competitor names.
- Shows: competitor name, mention count, and a one-word context tag (Comparison, Switching from, Currently using, etc.)
- Click a row → see exact conversation excerpts where this competitor was mentioned.
- This is competitive intelligence gold — the admin knows exactly which competitors their prospects are evaluating against.

---

## Intent Signals Page (`/intent`)

### Purpose
Understand which prospects showed buying intent, which were just exploring, and which had a negative experience. This turns anonymous demo sessions into a lightweight lead scoring system.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Intent Signals                       [Last 30 days ▾]           │
│                                                                  │
│  ┌─ SENTIMENT OVERVIEW ─────────────────────────────────────┐    │
│  │                                                          │    │
│  │  Overall demo sentiment:                                  │    │
│  │                                                          │    │
│  │  Positive  ████████████████████████████████████  68%      │    │
│  │  Neutral   ██████████████                       24%      │    │
│  │  Negative  ████                                  8%      │    │
│  │                                                          │    │
│  │  Trend: Sentiment improving ▲ (+4% positive vs last 30d) │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ INTENT INDICATORS ──────────────────────────────────────┐    │
│  │                                                          │    │
│  │  High buying intent signals detected in sessions:         │    │
│  │                                                          │    │
│  │  Signal                      Occurrences  % of sessions  │    │
│  │  ─────────────────────────────────────────────────────── │    │
│  │  Asked about pricing/plans   28           20%            │    │
│  │  Asked about trial/signup    22           15%            │    │
│  │  Compared with current tool  18           13%            │    │
│  │  Asked about onboarding      14           10%            │    │
│  │  Asked about team/seats      11            8%            │    │
│  │  Requested human contact     26           18%            │    │
│  │  Explored 5+ features        17           12%            │    │
│  │  Session lasted 15+ min      12            8%            │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ SESSION INTENT BREAKDOWN ───────────────────────────────┐    │
│  │                                                          │    │
│  │  Filter: [All ▾]  [Positive ▾]  [High intent only ☐]    │    │
│  │                                                          │    │
│  │  Date          Duration  Intent     Score  Key Signals   │    │
│  │  ─────────────────────────────────────────────────────── │    │
│  │  Today, 2:40p  12:34     Positive   8/10   pricing,      │    │
│  │                                            trial, 6      │    │
│  │                                            features      │    │
│  │  Today, 11:02  4:12      Neutral    4/10   quick look,   │    │
│  │                                            1 feature     │    │
│  │  Yesterday     18:45     Positive   9/10   pricing,      │    │
│  │                                            onboarding,   │    │
│  │                                            handoff req   │    │
│  │  Mar 13        6:02      Negative   2/10   confusion,    │    │
│  │                                            "doesn't      │    │
│  │                                            work"         │    │
│  │                                                          │    │
│  │  [View all sessions →]                                   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ NEGATIVE EXPERIENCE PATTERNS ───────────────────────────┐    │
│  │                                                          │    │
│  │  Why some sessions go poorly:                             │    │
│  │                                                          │    │
│  │  Pattern                    Sessions  Action              │    │
│  │  ─────────────────────────────────────────────────────── │    │
│  │  Agent couldn't answer      7         [Review gaps →]    │    │
│  │  Prospect seemed confused   4         [Review sessions →]│    │
│  │  Early abandonment (<2min)  12        [Check loading →]  │    │
│  │  Repeated questions         3         [Review clarity →] │    │
│  │                                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Intent Signals — Detailed

**Sentiment Overview:**
Three-bar horizontal breakdown — Positive / Neutral / Negative.
Sentiment is computed per-session by analyzing the prospect's messages:
- **Positive signals**: "That's cool," "This is exactly what I need," "How do I sign up," excitement, pricing questions, trial requests
- **Neutral signals**: Factual questions without emotional valence, brief responses, exploratory behavior
- **Negative signals**: "That's confusing," "I expected more," "This doesn't seem right," frustration indicators, very short sessions with few interactions

The AI classifies each session into one of three buckets. It's not perfect but it's directionally useful.

**Intent Indicators Table:**
Specific behavioral signals that correlate with buying intent, tracked across all sessions:

| Signal | What it detects | Why it matters |
|--------|----------------|---------------|
| Asked about pricing/plans | Prospect mentioned cost, pricing, plans | Active purchase consideration |
| Asked about trial/signup | "Free trial," "how do I start," "sign up" | Ready to convert |
| Compared with current tool | "We currently use X," "switching from Y" | Evaluating replacement |
| Asked about onboarding | "How long to set up," "migration," "import" | Planning adoption |
| Asked about team/seats | "How many users," "team plan," "seats" | Sizing for purchase |
| Requested human contact | Triggered escalation / asked for sales call | Wants to buy, needs human |
| Explored 5+ features | Navigated to 5 or more product sections | Deep interest |
| Session lasted 15+ min | Long session duration | High engagement |

Each signal has an occurrence count and percentage of total sessions. This table IS the lead scoring rubric.

**Session Intent Breakdown:**
Every session gets a computed intent score (1-10) based on the signals above. The table shows each session with its score and which signals were detected.

Filterable by intent level. An admin can filter for "Score 7+" to see their hottest prospects — even though the sessions are anonymous, they know WHICH sessions had high intent and can review the transcripts to understand what these prospects care about.

**Negative Experience Patterns:**
When sessions go poorly, why? This section clusters negative sessions into patterns:
- **Agent couldn't answer**: Knowledge gaps. Links to unanswered questions.
- **Prospect seemed confused**: The agent's explanations weren't clear. Links to specific sessions for review.
- **Early abandonment**: Prospects left in under 2 minutes. Could be loading issues, bad first impression, or wrong audience.
- **Repeated questions**: Prospect asked the same thing multiple ways, suggesting the agent's first answer wasn't satisfying.

Each pattern has an actionable link — "Review gaps," "Check loading," etc. — that takes the admin to the relevant section to fix the issue.

---

## Contacts Page (`/contacts`)

### Purpose
Track prospect interactions over time. Even with anonymous sessions, each session represents a unique prospect touchpoint.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Contacts                             [Export ↓]                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                            │  │
│  │  ID         Sessions  Last Visit    Intent   Features      │  │
│  │  ──────────────────────────────────────────────────────── │  │
│  │  #d8f2     1         Today, 2:40p   8/10    Sequences,    │  │
│  │                                              Warmup,       │  │
│  │                                              Lead Finder   │  │
│  │  #a4c1     2         Today, 11:02   6/10    Lead Finder,  │  │
│  │                                              Inbox         │  │
│  │  #9b3e     1         Yesterday      9/10    Sequences,    │  │
│  │                                              Pricing,      │  │
│  │                                              Integrations  │  │
│  │  #7d2f     1         Mar 13         2/10    Sequences     │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Note: Sessions are currently anonymous. Future: optional        │
│  email capture before demo starts.                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

For POC: Each session generates an anonymous contact ID (short hash). The table shows their session history, intent score, and what they explored.

This page exists primarily as a **structural placeholder** that becomes powerful when identity capture is added post-POC (optional email gate, CRM integration, etc). For now it provides a session-centric view of prospects rather than a time-centric view.

---

## Revised Navigation Map

```
Sidebar
├── WORKSPACE
│   ├── Dashboard (/dashboard)
│   │     Key metrics, session volume chart, engagement stats,
│   │     top features, attention needed, recent sessions
│   │
│   ├── Products (/products)
│   │   └── [Product] (/products/[id])
│   │       ├── Overview tab — identity, connection, setup checklist
│   │       ├── Knowledge tab — sources, entries, test agent
│   │       ├── Agent tab — persona, response behavior, guardrails
│   │       ├── Sessions tab — filtered to this product
│   │       └── Share tab — link, starters, session config, appearance
│   │
│   ├── Sessions (/sessions)
│   │     All sessions across products, filterable
│   │     └── [Session] (/sessions/[id]) — transcript + insights
│   │
│   └── Contacts (/contacts)
│         Anonymous prospect profiles with session history
│
├── INTELLIGENCE
│   ├── Analytics (/analytics)
│   │     Volume, timing, engagement depth, feature map, funnel
│   │
│   ├── Keywords & Topics (/keywords)
│   │     Top keywords, question themes, competitor mentions
│   │
│   └── Intent Signals (/intent)
│         Sentiment, buying signals, intent scores, negative patterns
│
├── CONFIGURE
│   ├── Settings (/settings)
│   ├── Integrations (/integrations) — placeholder
│   └── Help (/help)
│
└── Product Switcher (bottom)
    Filters Dashboard, Analytics, Keywords, Intent by product
```

---

## Chart & Data Visualization Design Rules

Since we're adding real charts and data visualizations, they need to follow the same design philosophy:

**Chart style:**
- No 3D effects. Ever.
- No gradient fills. Solid colors only.
- Accent color (amber) for primary data series. --text-tertiary for secondary/comparison.
- No background grids. Only a subtle baseline (1px, --border-subtle).
- Axis labels: --text-xs, --text-tertiary. Minimal — only show what's needed to read the chart.
- No legends when there's only one data series.
- Tooltips on hover: Clean, dark background (--bg-elevated equivalent), small, showing exact values.
- Bar charts: 4px top radius. 60% opacity default, 100% on hover.
- Area charts: 2px line in accent, 6% opacity fill.
- No pie charts. Ever. Use horizontal bars for proportions.
- No donut charts. Use the stacked horizontal bar or simple numbers.

**Data display preference hierarchy:**
1. A single number with context (best — "142 sessions, +23%")
2. A simple horizontal bar list (good — ranked features)
3. A bar or area chart (when time-series matters)
4. A table (when multiple dimensions need to be compared)
5. Never: pie charts, donut charts, radar charts, gauges, 3D anything

**Empty data states:**
When there isn't enough data for a chart (e.g., first week, only 3 sessions):
- Don't show an empty chart with zero bars
- Show the metric as a simple number instead
- Add context: "Analytics will be more meaningful after 20+ sessions"
- Charts only render when there's enough data to be statistically interesting

**Library recommendation:**
Recharts for React. It's the cleanest, most customizable, and integrates well with Tailwind. No Chart.js (too opinionated on styling). No D3 directly (overkill for these charts).

# DemoAgent: Technical Foundation & Performance Spec
## Speed as Architecture, Not Afterthought

---

## Part 0: Why This Document Exists

Most products bolt on performance optimization after they're built. That's expensive and often impossible — you can't make a slow architecture fast with caching tricks. DemoAgent treats speed as a structural decision. Every technology choice, every component pattern, every data-fetching strategy in this document was selected because it's the fastest option that doesn't sacrifice developer experience.

The target: **every interaction feels instant.** Not "fast." Instant. The user clicks, the UI responds in the same frame. Data appears before they consciously expect it. Pages don't "load" — they're already there.

This document is the technical constitution. Every implementation decision should be tested against it.

---

## Part 1: Technology Choices — With Reasoning

### Framework: Next.js 15 (App Router)

**Why Next.js and not Vite + React SPA:**
- Server Components reduce the JavaScript shipped to the browser. Admin console pages like Settings, Product Overview, Knowledge list — these are mostly static content with small interactive islands. Server Components render them on the server, send HTML, ship zero JS for the static parts.
- Streaming SSR with Suspense. The page shell renders instantly, data streams in. The user sees the layout before the data arrives. No blank white screen while APIs respond.
- Built-in route-based code splitting. Each page only loads its own code. The Analytics page with Recharts doesn't add a single byte to the Dashboard load.
- Edge-ready. Deploy to Vercel Edge or Cloudflare Workers. Response from the nearest edge node, not a single origin server.
- Image optimization, font optimization, metadata handling — all built in, all automatic.

**Why not Remix, SvelteKit, or Astro:**
- Remix: Excellent for forms and mutations, but its data loading model (loaders on every navigation) adds latency for dashboard-style apps where you want client-side caching. Next.js + React Query gives us more control.
- SvelteKit: Faster runtime, but smaller ecosystem. We need Recharts, shadcn/ui, Framer Motion — all React-native. Svelte alternatives exist but are less mature.
- Astro: Perfect for content sites, not for highly interactive apps with real-time WebSocket connections and complex state.

### Rendering Strategy: Hybrid (Per-Route Decision)

Not every page should render the same way. We pick the optimal strategy per route:

```
Route                      Strategy         Why
─────────────────────────────────────────────────────────────
/dashboard                 SSR + Stream     Needs fresh data on every visit.
                                            Shell renders instantly, metrics 
                                            stream in via Suspense boundaries.

/products                  SSR              Product list should always be fresh.
                                            Small payload. Fast.

/products/[id] (tabs)      SSR + Client     Tab shell is SSR. Tab content 
                                            switches client-side without 
                                            full page reload. Active tab 
                                            data fetched client-side with 
                                            React Query (cached).

/analytics                 Client           Heavy charts. Ship a lightweight 
                                            shell SSR, load chart data and 
                                            Recharts client-side. Charts are 
                                            lazy-imported so they don't block 
                                            initial paint.

/keywords                  Client           Same as analytics — data-heavy,
                                            interactive, lazy-loaded.

/intent                    Client           Same pattern.

/sessions                  SSR + Stream     Table renders SSR. Rows stream in.
                                            Pagination is client-side.

/sessions/[id]             SSR              Transcript is static content.
                                            Perfect for SSR. Fast first paint.

/demo/[sessionId]          Client           The demo stage is entirely 
                                            client-side. WebSocket connection,
                                            live browser stream, real-time 
                                            chat. No SSR benefit here.

/settings                  SSR              Static forms. SSR is fastest.
```

### Styling: Tailwind CSS v4

**Why Tailwind and not CSS Modules, styled-components, or Panda CSS:**
- Zero runtime cost. Tailwind compiles to static CSS at build time. Styled-components and Emotion inject styles at runtime — that's JavaScript execution on every render.
- Atomic CSS means styles are heavily deduplicated. The entire DemoAgent CSS bundle will be under 15KB gzipped, regardless of how many components we build.
- Tailwind v4 uses the Rust-based Lightning CSS engine. Build times are near-instant.
- Design tokens map directly to Tailwind's configuration. The color system, spacing scale, typography — all defined once in `tailwind.config.ts`, used everywhere with utility classes.
- No naming debates. No BEM. No specificity wars. Just utilities.

**Why not vanilla CSS with CSS variables:**
- CSS variables for tokens, yes — Tailwind generates those. But writing raw CSS for every component is slower to develop and harder to keep consistent across a team.

**Tailwind configuration approach:**
```
// tailwind.config.ts defines the ENTIRE design system:
// - Colors (all the tokens from the design spec)
// - Typography scale
// - Spacing scale (8px grid)
// - Border radius presets
// - Shadow presets (almost none)
// - Animation presets
// 
// NO arbitrary values in components (no `w-[347px]`).
// If a value isn't in the config, it doesn't belong in the UI.
// Exception: one-off layout measurements like sidebar width.
```

### Component Library: shadcn/ui (Radix primitives)

**Why shadcn/ui and not Headless UI, Ark UI, or building from scratch:**
- shadcn/ui gives us unstyled, accessible Radix primitives with a default Tailwind styling layer that we fully own and customize. We copy the components into our repo — no dependency on a package that might change.
- Every component is a file we control. We modify them to match our design system exactly. No fighting a library's opinions.
- Radix primitives handle the hard accessibility work: focus management, keyboard navigation, screen reader support, ARIA attributes. We don't reinvent this.
- The components are tiny. A Button is ~20 lines. A Dialog is ~40 lines. No bloat.

**What we use from shadcn/ui:**
```
Core (use as-is, restyle):     Extended (compose from primitives):
─────────────────────────       ──────────────────────────────────
Button                          DataTable (built on top of Table)
Input                           CommandPalette (built on Command)
Textarea                        MetricCard (custom)
Select                          SourceList (custom)
Dialog (rare — destructive only) TranscriptView (custom)
Dropdown Menu                   ChartContainer (custom)
Tooltip (minimal use)
Table
Tabs
Badge
Toast
Separator
Command (for ⌘K palette)
```

**What we DON'T use:**
- Accordion (we use simple collapsible sections with CSS)
- Card (we build our own — shadcn's Card is too opinionated)
- Form (we use plain controlled inputs, not form abstractions)
- Calendar, DatePicker (no date picking in POC)
- Sheet (no sliding panels — we use page-level layouts)

### State Management: Zustand + React Query (TanStack Query)

**Why this combination and not Redux, Jotai, or React Context:**

Two types of state, two tools:

**Server state (API data)** → React Query
- Dashboard metrics, session lists, knowledge entries, analytics data — all comes from the server.
- React Query handles: fetching, caching, background refetching, stale-while-revalidate, optimistic updates, pagination, and infinite scroll.
- Without React Query, every page would show a loading state on every visit. With it, data is cached and shown instantly on revisit, then silently refreshed in the background.
- The stale time for different data types:
  ```
  Dashboard metrics:     30 seconds (refresh often)
  Session list:          60 seconds
  Knowledge entries:     5 minutes (changes infrequently)
  Product config:        5 minutes
  Analytics data:        5 minutes (computed, expensive)
  Agent config:          10 minutes (rarely changes)
  ```

**Client state (UI state)** → Zustand
- Sidebar collapsed/expanded, active product context, active tab, chat input draft, theme preference.
- Zustand is 1KB. It's a single function call to create a store. No providers wrapping the tree. No boilerplate.
- Persists selected state to localStorage (sidebar preference, product selection) automatically.

**Why not Redux:**
- Redux is 7KB + toolkit overhead, requires Provider wrapping, and the boilerplate-to-value ratio is terrible for an app this size. We don't need time-travel debugging or middleware chains.

**Why not React Context for everything:**
- Context triggers re-renders on ALL consumers when ANY value changes. For frequently-updating state (like the demo stage chat messages), this destroys performance. Zustand's selector-based subscriptions only re-render the specific components that use the specific value that changed.

**Why not Jotai:**
- Jotai is excellent but atomic state becomes hard to reason about at scale. Zustand's centralized stores (one for admin, one for demo) are easier to maintain and debug.

### Real-Time Communication: Socket.IO

**For the demo stage** (chat + agent status + navigation events):
- Socket.IO over plain WebSockets because it handles reconnection, fallback to long-polling, rooms (each session is a room), and binary data — all out of the box.
- The demo stage opens ONE socket connection. All real-time data flows through it:
  - Chat messages (both directions)
  - Agent status (thinking, navigating, idle)
  - Navigation events (what the agent is doing in the browser)
  - Session lifecycle (started, ending, ended)

**For the admin console:**
- No persistent WebSocket needed. React Query's background refetching handles data freshness.
- Exception: If we later add "watch a live session" to admin, that would need a socket. Not in POC scope.

### Charts: Recharts (Lazy-Loaded)

**Why Recharts and not Chart.js, Nivo, or Tremor:**
- Recharts is built on React and D3. Components are declarative JSX. Integrates naturally with our component model.
- It's tree-shakeable. Import only `BarChart` and `Bar` for the dashboard — don't ship `PieChart` code that we'll never use.
- Styling follows our design system. We pass Tailwind-generated CSS variables directly.
- Chart.js is canvas-based — harder to style consistently with the rest of the UI, and doesn't participate in React's rendering lifecycle.
- Nivo is heavier. Tremor is opinionated and adds its own design system layer.

**Critical: Charts are NEVER in the initial bundle.**
```typescript
// WRONG — imports chart library on page load
import { BarChart, Bar } from 'recharts';

// RIGHT — lazy import, only loads when visible
const BarChart = lazy(() => 
  import('recharts').then(mod => ({ default: mod.BarChart }))
);
```
Every chart component is wrapped in a Suspense boundary with a lightweight skeleton placeholder. The user sees the page layout instantly; charts fade in as the library loads.

### Animation: Framer Motion (Minimal, Targeted)

**Why Framer Motion and not CSS-only or GSAP:**
- Most animations ARE CSS-only (hover states, transitions, the thinking shimmer). Framer Motion is only for:
  - Page transitions (subtle fade + translateY)
  - List item enter/exit (staggered appearance of chat messages, table rows)
  - Layout animations (tab content switching, panel resize)
  - AnimatePresence (clean exit animations before unmount)
- Framer Motion's `LazyMotion` feature loads only the animation features we use, not the entire library.
- GSAP is for complex timeline animations. We have none.

```typescript
// Load only what we need — NOT the full 30KB bundle
import { LazyMotion, domAnimation } from 'framer-motion';

// Wrap the app once
<LazyMotion features={domAnimation} strict>
  {children}
</LazyMotion>
```

### Icons: Lucide React (Tree-Shakeable)

**Why Lucide and not Heroicons, Phosphor, or custom SVGs:**
- Tree-shakeable. Import `import { Search } from 'lucide-react'` and only that one icon's SVG ships. The other 1400+ icons add zero bytes.
- Consistent stroke-style aesthetic that matches our design system (1.5px stroke, rounded joins).
- 18px and 20px render cleanly (designed for it, unlike some icon sets that look fuzzy at small sizes).

**Why not an icon sprite or custom SVGs:**
- Icon sprites prevent tree-shaking — you ship every icon even if you use 20.
- Custom SVGs are ideal aesthetically but time-consuming to create 40+ icons for a POC.

### Fonts: Variable Fonts via next/font

```typescript
// One font file, all weights. No layout shift. No FOUT.
import { Instrument_Sans } from 'next/font/google';

const font = Instrument_Sans({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-body',
  weight: ['400', '500', '600'],  // Only the weights we use
});
```

**Why `next/font`:**
- Self-hosts the font files. No external request to Google Fonts at runtime.
- Automatic `font-display: swap` with zero layout shift (generates matching size-adjust CSS).
- Font files are preloaded in the HTML `<head>`. Available on first paint.

**Font loading strategy:**
- Instrument Sans for body/UI: Loaded on every page (small, variable font file).
- Satoshi for display headings: Loaded on pages that use it (marketing pages, demo stage header). Use `next/font/local` to load from `/public/fonts/`.
- JetBrains Mono for code/data: Loaded lazily only on pages that show code or session IDs.

---

## Part 2: Performance Budgets

Hard limits. If we exceed these, we fix it before shipping.

### Bundle Size Budgets

```
Route                   First Load JS    Shared Chunks
──────────────────────────────────────────────────────
/ (redirect)            < 5KB            —
/dashboard              < 45KB           ~30KB shared
/products               < 35KB           ~30KB shared
/products/[id]          < 40KB           ~30KB shared
/analytics              < 60KB*          ~30KB shared
/keywords               < 50KB*          ~30KB shared
/intent                 < 50KB*          ~30KB shared
/sessions               < 35KB           ~30KB shared
/sessions/[id]          < 30KB           ~30KB shared
/demo/[sessionId]       < 55KB           ~15KB shared
/settings               < 25KB           ~30KB shared

* Analytics pages are larger because of Recharts.
  But Recharts is lazy-loaded, so first paint 
  is still under 40KB. Charts load after.

Shared chunk includes: React, Zustand, React Query 
core, Tailwind runtime (basically zero), layout 
components, sidebar, fonts.

Total CSS: < 20KB gzipped (Tailwind purged output)
```

### Core Web Vitals Targets

```
Metric                  Target          Unacceptable
──────────────────────────────────────────────────────
LCP (Largest Content)   < 1.2s          > 2.5s
FID (First Input)       < 50ms          > 100ms
CLS (Layout Shift)      < 0.05          > 0.1
INP (Interaction Next)  < 100ms         > 200ms
TTFB (Time to First B)  < 200ms         > 500ms
FCP (First Content P)   < 0.8s          > 1.5s
```

### Interaction Speed Targets

```
Action                          Target Response
──────────────────────────────────────────────────
Sidebar navigation click        < 50ms (instant, client-side)
Tab switch within product       < 50ms (instant, client-side)
Table row click                 < 100ms (navigate to detail)
Form field save (autosave)      < 200ms (optimistic, confirmed bg)
Knowledge search                < 150ms (client-side filtering)
Command palette open            < 50ms (always in memory)
Command palette search          < 100ms (local fuzzy search)
Chat message send               < 100ms (optimistic append)
Chart hover tooltip             < 16ms (same frame)
Modal open                      < 100ms (pre-rendered, opacity)
Toast appear                    < 50ms (pre-positioned)
Page load (cached, SPA nav)     < 100ms
Page load (fresh, SSR)          < 500ms
```

---

## Part 3: Component Architecture Patterns

### Pattern 1: Optimistic UI Everywhere

Every mutation (save, delete, create, update) follows this pattern:

```typescript
// Example: Updating product description
const updateProduct = useMutation({
  mutationFn: (data) => api.updateProduct(productId, data),
  
  // BEFORE the request: update the UI immediately
  onMutate: async (newData) => {
    // Cancel any outgoing refetches
    await queryClient.cancelQueries(['product', productId]);
    
    // Snapshot previous value (for rollback)
    const previous = queryClient.getQueryData(['product', productId]);
    
    // Optimistically update the cache
    queryClient.setQueryData(['product', productId], (old) => ({
      ...old,
      ...newData,
    }));
    
    return { previous };
  },
  
  // If the request fails: rollback
  onError: (err, newData, context) => {
    queryClient.setQueryData(['product', productId], context.previous);
    toast.error('Failed to save. Your changes have been reverted.');
  },
  
  // After success: silently confirm
  onSettled: () => {
    queryClient.invalidateQueries(['product', productId]);
  },
});
```

The user NEVER waits for a server response to see their change reflected. The UI updates first, the server confirms in the background.

### Pattern 2: Skeleton-First Loading

Every data-dependent component has a matching skeleton:

```typescript
// The component
function MetricCard({ title, value, trend }) {
  return (
    <div className="p-5">
      <p className="text-sm text-secondary">{title}</p>
      <p className="text-2xl text-primary mt-1">{value}</p>
      <p className="text-sm mt-1">{trend}</p>
    </div>
  );
}

// Its skeleton — SAME dimensions, no layout shift
function MetricCardSkeleton() {
  return (
    <div className="p-5">
      <div className="h-4 w-24 bg-gray-100 rounded animate-shimmer" />
      <div className="h-7 w-16 bg-gray-100 rounded animate-shimmer mt-1" />
      <div className="h-4 w-20 bg-gray-100 rounded animate-shimmer mt-1" />
    </div>
  );
}
```

Rules for skeletons:
- Match the EXACT dimensions of the real component. No layout shift when data arrives.
- Use a single `animate-shimmer` class (CSS gradient sweep animation). No per-skeleton animation variation.
- Show skeletons for a MINIMUM of 200ms even if data arrives faster. Prevents flash-of-skeleton that feels glitchy.
- Never show a spinner. Spinners communicate "waiting." Skeletons communicate "content is coming."

### Pattern 3: Virtualized Long Lists

Any list that could exceed 50 items uses virtualization:

```typescript
// Sessions list — could have hundreds of rows
// Only renders the ~15 visible rows, not all 500

import { useVirtualizer } from '@tanstack/react-virtual';

function SessionList({ sessions }) {
  const parentRef = useRef(null);
  
  const virtualizer = useVirtualizer({
    count: sessions.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56, // row height in px
    overscan: 5,            // render 5 extra above/below viewport
  });

  return (
    <div ref={parentRef} className="h-full overflow-auto">
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <SessionRow 
            key={sessions[virtualRow.index].id}
            session={sessions[virtualRow.index]}
            style={{
              transform: `translateY(${virtualRow.start}px)`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
```

**Where virtualization is required:**
- Session list (could be 1000+)
- Knowledge entries list (could be 500+)
- Transcript messages in session detail (could be 100+)
- Keyword list (could be 200+)

**Where virtualization is NOT needed:**
- Product list (unlikely to exceed 10)
- Dashboard recent sessions (capped at 5)
- Sidebar navigation (fixed items)
- Starter questions (capped at 10)

### Pattern 4: Debounced Autosave

All form inputs autosave with debouncing:

```typescript
function useAutosave(value, saveFn, delay = 800) {
  const [status, setStatus] = useState('idle'); // idle | saving | saved
  
  useEffect(() => {
    setStatus('idle');
    
    const timer = setTimeout(async () => {
      setStatus('saving');
      await saveFn(value);
      setStatus('saved');
      
      // Fade "Saved" indicator after 2 seconds
      setTimeout(() => setStatus('idle'), 2000);
    }, delay);
    
    return () => clearTimeout(timer);
  }, [value]);
  
  return status;
}

// Usage in a component
function ProductDescription({ product }) {
  const [desc, setDesc] = useState(product.description);
  const status = useAutosave(desc, (val) => 
    api.updateProduct(product.id, { description: val })
  );
  
  return (
    <div>
      <textarea value={desc} onChange={(e) => setDesc(e.target.value)} />
      {status === 'saving' && <span className="text-tertiary text-xs">Saving...</span>}
      {status === 'saved' && <span className="text-tertiary text-xs">Saved</span>}
    </div>
  );
}
```

Debounce delay by input type:
```
Text inputs (name, description):     800ms
URL inputs:                          1200ms (user might be pasting)
Textarea (custom instructions):      1000ms
Toggle/radio changes:                 0ms (save immediately)
Slider changes:                      500ms
```

### Pattern 5: Pre-fetching Adjacent Routes

When the user hovers over a navigation item, prefetch that page's data:

```typescript
// In the sidebar
function NavItem({ href, children }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  
  const handleMouseEnter = () => {
    // Prefetch the route (Next.js prefetches the JS bundle)
    router.prefetch(href);
    
    // Prefetch the data (React Query fetches the API data)
    if (href === '/dashboard') {
      queryClient.prefetchQuery({
        queryKey: ['dashboard-metrics'],
        queryFn: fetchDashboardMetrics,
        staleTime: 30_000,
      });
    }
  };
  
  return (
    <Link href={href} onMouseEnter={handleMouseEnter}>
      {children}
    </Link>
  );
}
```

By the time the user clicks, both the code AND the data are already cached. The navigation feels teleport-fast.

**Prefetch rules:**
- Prefetch on hover for sidebar navigation items.
- Prefetch on hover for table rows (prefetch the detail page).
- Prefetch on focus for tab buttons (prefetch the tab content).
- Do NOT prefetch everything eagerly on page load — that wastes bandwidth.
- Prefetch is a hint, not a guarantee. The browser can ignore it under resource pressure.

### Pattern 6: Streaming Data Boundaries

For SSR pages, use Suspense boundaries to stream sections independently:

```tsx
// Dashboard page — shell renders instantly, sections stream in

export default function Dashboard() {
  return (
    <div>
      <h1>Good afternoon, Malav</h1>
      
      {/* These four cards can load independently */}
      <div className="grid grid-cols-4 gap-4">
        <Suspense fallback={<MetricCardSkeleton />}>
          <SessionCountCard />
        </Suspense>
        <Suspense fallback={<MetricCardSkeleton />}>
          <AvgDurationCard />
        </Suspense>
        <Suspense fallback={<MetricCardSkeleton />}>
          <CompletionRateCard />
        </Suspense>
        <Suspense fallback={<MetricCardSkeleton />}>
          <HandoffRateCard />
        </Suspense>
      </div>
      
      {/* Chart section loads after metrics */}
      <Suspense fallback={<ChartSkeleton />}>
        <SessionVolumeChart />
      </Suspense>
      
      {/* Table loads last */}
      <Suspense fallback={<TableSkeleton rows={5} />}>
        <RecentSessions />
      </Suspense>
    </div>
  );
}
```

The user sees the page structure and headers immediately. Metric cards pop in as each API call resolves (they're independent — one slow query doesn't block the others). Charts load last because they're heaviest.

---

## Part 4: Asset Optimization

### Image Strategy

**Admin console:** Almost no images. Icons are SVG (via Lucide). Empty states use minimal line illustrations — SVG, not PNG. Product logos are user-uploaded — optimize on upload (resize to 200x200 max, convert to WebP, serve from CDN).

**Demo stage:** The product logo in the header. Same optimization. The browser stream is an iframe, not an image — no optimization needed from our side.

**If any images are needed:**
```tsx
// ALWAYS use next/image — never raw <img>
import Image from 'next/image';

<Image 
  src={logoUrl}
  alt={productName}
  width={120}
  height={32}
  priority          // Above the fold — preload
  quality={85}      // Sufficient for logos
/>
```

### Font Subsetting

Load only Latin characters. We don't need Cyrillic, Greek, or Vietnamese character sets for the POC. This cuts font file size by 60-70%.

```typescript
const instrumentSans = Instrument_Sans({
  subsets: ['latin'],       // NOT ['latin', 'latin-ext', 'vietnamese']
  weight: ['400', '500'],   // NOT the full range
  display: 'swap',
});
```

### CSS Optimization

Tailwind v4 purges unused styles automatically. But we enforce additional discipline:

```
Rules:
- No @apply in component files. It bloats the CSS and defeats 
  Tailwind's deduplication.
- Shared patterns use React components, not CSS classes.
  (A "Card" is a React component with utility classes, 
   not a .card CSS class.)
- No CSS-in-JS. No styled-components. No Emotion. 
  No runtime style injection of any kind.
- Animations use CSS @keyframes defined once in globals.css, 
  not inline styles.
- Dark mode uses Tailwind's `dark:` variant backed by a 
  CSS class on <html>. No runtime theme calculation.
```

---

## Part 5: Demo Stage — Real-Time Performance

The demo stage has unique performance requirements because it's real-time.

### WebSocket Message Handling

```typescript
// Messages arrive from the server via Socket.IO
// We handle them WITHOUT causing unnecessary re-renders

const useDemoStore = create((set, get) => ({
  messages: [],
  agentStatus: 'idle',
  
  // Append a message WITHOUT replacing the entire array
  addMessage: (msg) => set((state) => ({
    messages: [...state.messages, msg],
  })),
  
  // Update status WITHOUT touching messages
  setAgentStatus: (status) => set({ agentStatus: status }),
}));

// In components, subscribe to ONLY what you need:

// ChatPanel only re-renders when messages change
const messages = useDemoStore((s) => s.messages);

// StatusIndicator only re-renders when status changes
const status = useDemoStore((s) => s.agentStatus);

// DemoScreen NEVER re-renders from state changes
// (it's an iframe — state doesn't affect it)
```

### Chat Message Streaming

When the agent streams a response (token by token), we DON'T create a new message object per token. That would mean hundreds of state updates per response.

```typescript
// WRONG — re-renders on every token
socket.on('agent_token', (token) => {
  setMessages(prev => {
    const last = prev[prev.length - 1];
    return [...prev.slice(0, -1), { ...last, text: last.text + token }];
  });
});

// RIGHT — accumulate tokens in a ref, batch update
const streamBufferRef = useRef('');
const flushIntervalRef = useRef(null);

socket.on('agent_stream_start', () => {
  streamBufferRef.current = '';
  // Add empty message placeholder
  addMessage({ role: 'agent', text: '', streaming: true });
  
  // Flush buffer to state every 50ms (20fps — smooth enough)
  flushIntervalRef.current = setInterval(() => {
    if (streamBufferRef.current) {
      updateLastMessage(streamBufferRef.current);
      streamBufferRef.current = '';
    }
  }, 50);
});

socket.on('agent_token', (token) => {
  // Just append to buffer — no state update
  streamBufferRef.current += token;
});

socket.on('agent_stream_end', () => {
  clearInterval(flushIntervalRef.current);
  // Final flush
  finalizeLastMessage();
});
```

This batches token updates into ~20 state updates per second instead of potentially hundreds. The UI looks smooth; React doesn't thrash.

### Browser Stream (iframe) Performance

The Browserbase Live View iframe is the heaviest element on the page. Rules:

```
- The iframe loads AFTER the page shell renders. Use loading="lazy" 
  or mount it inside a useEffect.
- Give the iframe explicit width and height (no layout shift when it loads).
- The iframe has pointer-events: none (view-only mode). This means 
  NO event listeners on the iframe from our side. Zero overhead.
- If the iframe loses connection, show a reconnecting overlay 
  OVER the iframe (a positioned div), don't unmount and remount it.
- The iframe's src URL is set once. Never change it during a session 
  (that would reload the entire browser view).
```

---

## Part 6: Build & Deploy Configuration

### Next.js Configuration

```typescript
// next.config.ts
const config = {
  // Enable React strict mode (catches bugs, no production overhead)
  reactStrictMode: true,
  
  // Optimize package imports — tree-shake properly
  experimental: {
    optimizePackageImports: [
      'lucide-react',
      'recharts',
      'framer-motion',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
    ],
  },
  
  // Image optimization
  images: {
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 days
  },
  
  // Headers for caching
  async headers() {
    return [
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/fonts/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },
};
```

### Bundle Analysis

Run `npx @next/bundle-analyzer` before every major deployment. Check:
- No single route exceeds its budget (see Part 2)
- No duplicate packages (e.g., two versions of React)
- Recharts is only in analytics route chunks, not shared
- Framer Motion's `LazyMotion` is working (should be ~12KB, not ~30KB)

### Deployment Target

**Vercel** for POC (simplest, best Next.js integration, edge network). Configuration:

```
Framework: Next.js (auto-detected)
Build command: next build
Output: .next
Node.js version: 20.x
Region: Auto (nearest to most users — or explicitly set to 
        match your backend/Browserbase region to minimize latency)
Edge runtime: Enabled for API routes that don't need Node.js
```

---

## Part 7: Monitoring & Performance Regression Prevention

### Built-in Performance Tracking

```typescript
// Report Core Web Vitals to your analytics
// next.config.ts automatically captures these

export function reportWebVitals(metric) {
  // Send to your analytics endpoint
  if (metric.label === 'web-vital') {
    analytics.track('web-vital', {
      name: metric.name,    // CLS, FID, FCP, LCP, TTFB, INP
      value: metric.value,
      rating: metric.rating, // good, needs-improvement, poor
    });
  }
}
```

### Development Guardrails

```
1. React DevTools Profiler: Run monthly. No component should 
   render more than twice per user interaction.

2. Lighthouse CI: Run on every PR. Scores must be:
   Performance: > 90
   Accessibility: > 95
   Best Practices: > 90

3. Bundle size check: Automated in CI. PR fails if any 
   route exceeds its budget by more than 5KB.

4. No `useEffect` without cleanup. Prevents memory leaks 
   from subscriptions, timers, and event listeners.

5. No inline object/array creation in JSX props. 
   (Causes unnecessary re-renders.)
   
   // BAD — creates new object every render
   <Component style={{ color: 'red' }} />
   
   // GOOD — stable reference
   const style = useMemo(() => ({ color: 'red' }), []);
   <Component style={style} />
   
   // BEST — use Tailwind, no style object at all
   <Component className="text-red-500" />
```

---

## Part 8: Technology Summary

### The Stack

```
┌─ FRONTEND ─────────────────────────────────────────────────┐
│                                                             │
│  Framework:       Next.js 15 (App Router)                   │
│  Language:        TypeScript (strict mode)                   │
│  Styling:         Tailwind CSS v4                            │
│  Components:      shadcn/ui (Radix primitives)              │
│  State (client):  Zustand                                    │
│  State (server):  TanStack React Query v5                   │
│  Charts:          Recharts (lazy-loaded)                     │
│  Animation:       Framer Motion (LazyMotion)                │
│  Icons:           Lucide React                               │
│  Fonts:           Instrument Sans + Satoshi (next/font)     │
│  Real-time:       Socket.IO client                           │
│  Virtualization:  TanStack Virtual                           │
│  Forms:           Native controlled inputs + useAutosave    │
│  Linting:         ESLint + Prettier                          │
│  Types:           TypeScript strict, no `any`               │
│                                                             │
│  Total added JS deps: ~14                                   │
│  Approximate bundle: ~38KB shared + ~15-45KB per route      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### What We Explicitly DON'T Use

```
❌ CSS-in-JS (styled-components, Emotion)    — runtime overhead
❌ Redux / MobX                               — unnecessary complexity
❌ Axios                                      — fetch() is sufficient
❌ Moment.js / Luxon                          — date-fns or native Intl
❌ Lodash (full import)                       — native JS methods suffice
❌ Material UI / Ant Design / Chakra          — too opinionated, too heavy
❌ Storybook (for POC)                        — premature for team of one
❌ GraphQL                                    — REST is simpler for this data model
❌ tRPC                                       — good but adds type-sharing infra
❌ Prisma on frontend                         — backend concern only
❌ Any CSS framework besides Tailwind         — no Bootstrap, no Bulma
❌ jQuery                                     — obviously
```

### Dependency Count Discipline

The `package.json` should have no more than 20 direct production dependencies. Every additional dependency is a maintenance burden, a security surface, and a bundle size risk. Before adding a package, ask: "Can I do this with what I already have?" Usually the answer is yes.

```
Current approved dependency list (17 total):
──────────────────────────────────────────────
next                    — framework
react, react-dom        — UI library
typescript              — type safety
tailwindcss             — styling
@radix-ui/*             — accessible primitives (via shadcn)
zustand                 — client state
@tanstack/react-query   — server state
@tanstack/react-virtual — list virtualization
recharts                — charts
framer-motion           — animation
lucide-react            — icons
socket.io-client        — real-time communication
clsx                    — conditional class names
tailwind-merge          — merge Tailwind classes
date-fns                — date formatting (tiny, tree-shakeable)
class-variance-authority — component variants (shadcn dependency)
```

That's it. Seventeen dependencies for an entire SaaS platform. Every one earns its place.