# Claude Code Prompt: Frontend Design System for DemoAgent

You are a senior UX designer and frontend architect building the complete frontend for **DemoAgent** — an AI-powered interactive product demo platform. You will build two interfaces: an **Admin Console** (where SaaS owners configure their demo agent) and a **Demo Stage** (where prospects experience live AI-guided product walkthroughs).

---

## Brand Identity

### Name: DemoAgent
### Tagline: "Your AI Sales Engineer, always on."

### Brand Philosophy
DemoAgent is the **calm expert in the room**. Think of the best sales engineer you've ever met — someone who knows the product cold, never rushes, explains things with clarity, and makes you feel like you're the only person in the room. That's the energy this interface must project.

We are NOT:
- A chatbot widget (no bubble UI, no "how can I help you today" energy)
- A video conferencing tool (no Zoom/Meet aesthetic)
- A generic SaaS dashboard (no card-grid-with-charts sameness)

We ARE:
- A focused, intelligent workspace where a conversation drives a live product experience
- Notion's speed meets Linear's precision meets Apple Keynote's presentation quality
- The UI equivalent of a whisper, not a shout — every element earns its place

### Design Philosophy: "Disappearing Interface"
The best demo is one where the prospect forgets they're talking to software. The interface should fade into the background. The PRODUCT being demoed is the hero — our UI is the invisible stage crew making it all work.

Core principles:
1. **Content-first**: The live browser stream dominates. Our UI chrome is minimal.
2. **Progressive disclosure**: Show controls only when needed. Default state is clean.
3. **Calm confidence**: No loading spinners that feel anxious. No bouncing dots. Smooth, deliberate transitions that say "I've got this."
4. **Respects attention**: One focal point at a time. Never compete for the prospect's eyes.

### Mental Model
The mental model is a **private screening room**, not a call center.
- The prospect walks into a quiet, elegant room
- A large screen shows the product
- A knowledgeable guide sits beside them, narrating and navigating
- The prospect can ask anything, and the guide responds while showing relevant screens
- There's no rush, no agenda pushed — it follows the prospect's curiosity

---

## Color System

### Theme: Dark-dominant with warm accents
The interface should feel like a premium theater — dark background that makes the product demo screen "pop" like a cinema screen in a dark room.

```
// Core palette
--bg-primary: #0A0A0B          // Near-black, the void behind the stage
--bg-secondary: #141416        // Slightly lifted surface (panels, cards)
--bg-tertiary: #1C1C1F         // Hover states, active surfaces
--bg-elevated: #232326         // Modals, popovers, tooltips

// Text
--text-primary: #EDEDEF        // Primary text — not pure white, slightly warm
--text-secondary: #8E8E93      // Secondary, muted text
--text-tertiary: #5A5A5E       // Disabled, placeholder text

// Brand accent — warm amber/gold (the "spotlight")
--accent-primary: #E8A84C      // Primary actions, active states, the agent's "voice"
--accent-primary-hover: #D4963E
--accent-primary-muted: rgba(232, 168, 76, 0.12)  // Subtle highlights
--accent-primary-glow: rgba(232, 168, 76, 0.06)   // Ambient glow effects

// Semantic
--success: #34C759
--warning: #FF9F0A
--error: #FF453A
--info: #5AC8FA

// Borders
--border-subtle: rgba(255, 255, 255, 0.06)
--border-default: rgba(255, 255, 255, 0.1)
--border-active: rgba(232, 168, 76, 0.3)

// The product demo iframe/stream area
--demo-bg: #FFFFFF             // The demo screen itself is LIGHT (most SaaS products are)
--demo-border: rgba(255, 255, 255, 0.08)
--demo-shadow: 0 0 80px rgba(232, 168, 76, 0.03)  // Subtle warm glow around demo screen
```

### Light mode (Admin Console only)
The admin console should have a light mode option since admins use it for extended periods. The demo stage is always dark.

```
--bg-primary: #FFFFFF
--bg-secondary: #F7F7F8
--bg-tertiary: #EFEFEF
--text-primary: #1A1A1A
--text-secondary: #6B6B6B
--accent-primary: #D4963E      // Slightly deeper amber for light backgrounds
```

---

## Typography

### Font Stack
```
// Display / Headings: Satoshi (from Fontshare — free, distinctive, geometric)
--font-display: 'Satoshi', -apple-system, sans-serif

// Body / UI: Instrument Sans (from Google Fonts — clean, slightly humanist)  
--font-body: 'Instrument Sans', -apple-system, sans-serif

// Monospace (for technical details, session IDs, etc.)
--font-mono: 'JetBrains Mono', 'SF Mono', monospace
```

### Type Scale
```
--text-xs: 0.6875rem / 11px     // Timestamps, badges
--text-sm: 0.8125rem / 13px     // Secondary text, labels  
--text-base: 0.9375rem / 15px   // Body text, chat messages
--text-lg: 1.0625rem / 17px     // Section headers
--text-xl: 1.25rem / 20px       // Page titles
--text-2xl: 1.5rem / 24px       // Hero text
--text-3xl: 2rem / 32px         // Landing/marketing headers only
```

### Type Rules
- **Line height**: 1.5 for body text, 1.2 for headings
- **Letter spacing**: -0.01em for headings (slightly tight), 0 for body
- **Font weight**: 400 (regular) for body, 500 (medium) for labels/UI, 600 (semibold) for headings. Never use 700/bold in the app — it's too aggressive.
- **Max line width**: 65ch for readable paragraphs
- **Agent messages**: Use --font-body at --text-base, color --text-primary
- **User messages**: Same font but slightly different treatment (see conversation design below)

---

## Layout Architecture

### Demo Stage (Buyer-Side: The Main Event)

```
┌──────────────────────────────────────────────────────────┐
│  ┌─ Minimal Header ────────────────────────────────────┐ │
│  │  [DemoAgent logo]          [Product Name]   [End]   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ Demo Screen (70%) ─────┐  ┌─ Conversation (30%) ─┐  │
│  │                         │  │                       │  │
│  │   Live Browser Stream   │  │  Agent greeting       │  │
│  │   (iframe)              │  │                       │  │
│  │                         │  │  User question        │  │
│  │   This is THE hero.     │  │                       │  │
│  │   Maximum real estate.  │  │  Agent response       │  │
│  │   Subtle warm glow      │  │  + navigation cue     │  │
│  │   border around it.     │  │                       │  │
│  │                         │  │                       │  │
│  │                         │  │  ┌─ Input ──────────┐ │  │
│  │                         │  │  │ Ask anything...   │ │  │
│  │                         │  │  │          [Send]   │ │  │
│  │                         │  │  └──────────────────┘ │  │
│  └─────────────────────────┘  └───────────────────────┘  │
│                                                          │
│  ┌─ Context Bar (collapsible) ─────────────────────────┐ │
│  │  "Showing: Email Sequences → Create New"   [◀ ▶]   │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**Key layout rules:**
- Demo screen gets 70% width minimum. On smaller screens, stack vertically with demo on top.
- Conversation panel: 30% width, max 400px. Scrollable. Pinned input at bottom.
- Header: 48px max height. Barely there. Logo + product name + session controls.
- Context bar: Collapsible breadcrumb showing what the agent is currently demonstrating. Appears only when agent is actively navigating.
- NO sidebar navigation. NO hamburger menus. The conversation IS the navigation.
- Full viewport height. No scrolling on the outer frame — only inside the demo and chat panels.

### Admin Console (SaaS Owner Side)

```
┌──────────────────────────────────────────────────────────┐
│  ┌─ Sidebar (220px) ─┐  ┌─ Main Content ──────────────┐ │
│  │                    │  │                              │ │
│  │  [Logo]            │  │  Page Title                  │ │
│  │                    │  │  Subtitle / description      │ │
│  │  Products          │  │                              │ │
│  │  Knowledge Base    │  │  ┌─ Content Area ──────────┐ │ │
│  │  Agent Settings    │  │  │                         │ │ │
│  │  Customization     │  │  │  Forms, tables,         │ │ │
│  │  Analytics         │  │  │  configuration panels   │ │ │
│  │  Sessions          │  │  │                         │ │ │
│  │  Embed & Share     │  │  │                         │ │ │
│  │                    │  │  └─────────────────────────┘ │ │
│  │  ─────────         │  │                              │ │
│  │  Settings          │  │                              │ │
│  │  Billing           │  │                              │ │
│  └────────────────────┘  └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**Admin layout rules:**
- Notion-inspired: Clean sidebar, spacious content area
- Sidebar: 220px fixed, collapsible to 60px (icon-only)
- Content area: Max-width 800px centered (like Notion pages)
- For forms/config: Use section-based layout, not tabs. Scroll is fine.
- Tables: Minimal borders, generous row padding, hover highlights
- Speed: Every page should feel instant. Optimistic UI updates. No full-page loading states.

---

## Conversation Design (The Heart of the UX)

### Visual Cues for Agent vs. User — NOT Generic Chat Bubbles

This is the most important design element. We do NOT want:
- ❌ Generic chat bubbles (left/right alignment like WhatsApp)
- ❌ Avatar circles with generic bot icons
- ❌ "Typing..." with bouncing dots
- ❌ Any resemblance to Intercom, Drift, or Zendesk chat widgets

We DO want:

**Agent Messages:**
- Full-width within the conversation panel (no bubble, no background)
- Left-aligned text, rendered like clean prose
- A subtle warm amber accent line (2px) on the left edge — like a margin annotation
- When the agent is actively speaking/streaming, the accent line gently pulses (a slow, breathing opacity animation from 0.4 to 1.0, ~2s cycle)
- Agent messages that reference navigation include a small contextual chip below the text: `[→ Navigating to Sequences]` with a subtle animation (the arrow slides right slightly)
- No avatar. The agent IS the interface — it doesn't need a face.

```
│  ┌─ amber line                                          │
│  │  Here's how the email sequence builder works.        │
│  │  I'll walk you through creating a new sequence       │
│  │  with A/B testing variants.                          │
│  │                                                      │
│  │  [→ Opening Sequences → Create New]                  │
│  └──────────────────────────────────────────────────────│
```

**User Messages:**
- Slightly indented from right (not fully right-aligned, ~20px indent)
- Text color slightly dimmer than agent text (--text-secondary)
- A very subtle background tint: rgba(255, 255, 255, 0.03) — barely visible
- Rounded corners (8px) with a thin border (--border-subtle)
- Appears with a quick, clean fade-up animation (transform: translateY(4px) → 0, opacity 0 → 1, 200ms ease-out)

```
│                                                         │
│           ┌─────────────────────────────────────┐       │
│           │  How does the email warmup work?    │       │
│           └─────────────────────────────────────┘       │
│                                                         │
```

**Agent "Thinking" State:**
- When the agent is processing (before text starts streaming), show a single horizontal line that shimmers — a thin gradient sweep animation across a 2px line, using the amber accent color
- This replaces the bouncing dots. It's calm, confident, unhurried.
- Duration: The shimmer is continuous until text starts appearing
- Position: Where the next message will appear (in-place, no layout shift)

**Agent "Navigating" State:**
- When the agent is actively clicking/navigating the demo, show a small pill indicator at the top of the conversation panel:
  `◉ Navigating...` with the dot in amber, gently pulsing
- This replaces verbose "I'm now clicking on..." messages. The prospect can SEE it happening in the demo screen — the conversation doesn't need to narrate every click.

**Transition Moments:**
- When the agent finishes a walkthrough and pauses for the next question, add a subtle divider — not a horizontal line, but a gentle increase in spacing (24px → 40px gap) + a tiny timestamp in --text-tertiary
- This creates "breathing room" between exchanges without visual clutter

### Input Area Design
- Clean single-line input that expands to multi-line as needed (max 4 lines)
- Placeholder text rotates contextually: "Ask about any feature...", "Want to see something specific?", "What would you like to explore next?"
- Send button: An arrow icon (not text). Amber accent color. Only visible when there's text input.
- Optional: Microphone icon for voice input (future, but design the space for it now)
- Keyboard shortcut: Enter to send, Shift+Enter for newline
- Below the input: 2-3 suggested questions as small clickable pills (contextual, based on what the agent just showed)
  ```
  [How does A/B testing work?]  [Show me analytics]  [Pricing plans?]
  ```

---

## Components & Micro-interactions

### Buttons
- Primary: Amber fill, dark text, 8px radius, 36px height, medium weight text
- Secondary: Transparent with subtle border, 8px radius
- Ghost: No border, text only, underline on hover
- All buttons: 150ms ease transition on hover. No dramatic transforms. Subtle background shift.
- Disabled: 0.4 opacity, no pointer events

### Cards (Admin Console)
- Background: --bg-secondary
- Border: 1px --border-subtle
- Border-radius: 12px
- Padding: 20px
- Hover: border transitions to --border-default (150ms)
- No drop shadows by default. Very subtle shadow only on elevation (modals, popovers)

### Tables (Admin Console — Session History, Products, etc.)
- No visible borders between cells
- Thin bottom border on rows (--border-subtle)
- Row hover: background shifts to --bg-tertiary
- Header row: --text-secondary, uppercase --text-xs, letter-spacing 0.05em
- Cell padding: 12px vertical, 16px horizontal
- Sortable columns: Subtle chevron icon, amber when active

### Loading States
- Skeleton screens, not spinners
- Skeletons: Subtle shimmer animation (left-to-right gradient sweep)
- Matching the content shape they'll replace
- Duration: 800ms per sweep, infinite repeat
- For the demo screen loading: A centered, calm "Starting your demo..." text with the shimmer line below it

### Toasts & Notifications
- Appear from top-right, slide down
- Dark background (--bg-elevated), --text-primary
- Thin left accent border (color matches semantic: green for success, amber for info, red for error)
- Auto-dismiss after 4 seconds with a subtle height collapse animation
- Max 3 visible at once, stack downward

### Empty States
- Centered illustration (keep illustrations minimal — line-art style, monochrome with amber accent)
- Clear headline explaining what goes here
- Single CTA button
- Example for "No products configured": "Add your first product" with a brief description of what happens next

---

## Motion & Animation Principles

### Rules
1. **No animation longer than 400ms** in the UI (except the thinking shimmer and breathing pulse)
2. **Ease-out for entrances** (elements arriving): `cubic-bezier(0.16, 1, 0.3, 1)` — fast start, gentle landing
3. **Ease-in for exits** (elements leaving): `cubic-bezier(0.7, 0, 0.84, 0)` — gentle start, quick exit
4. **No bounce, no elastic, no spring** effects. This is a professional tool, not a toy.
5. **Reduce motion**: Respect `prefers-reduced-motion`. Fall back to instant transitions.
6. **Stagger children**: When multiple elements appear (like suggested questions), stagger by 50ms each

### Key Animations
- Page transitions (admin): Fade + subtle translateY (8px), 250ms
- Chat messages appearing: Fade + translateY (4px), 200ms
- Agent thinking shimmer: Linear gradient sweep, 800ms, infinite
- Agent breathing pulse (amber line): Opacity 0.4 → 1.0, 2s ease-in-out, infinite
- Navigation pill appearing: Scale(0.95) + opacity → scale(1) + opacity 1, 200ms
- Demo screen loading → loaded: Opacity 0 → 1, 400ms, with a very subtle scale (0.99 → 1)

---

## Responsive Behavior

### Breakpoints
```
--bp-sm: 640px    // Mobile
--bp-md: 768px    // Tablet  
--bp-lg: 1024px   // Small laptop
--bp-xl: 1280px   // Desktop
--bp-2xl: 1536px  // Large desktop
```

### Demo Stage responsive rules:
- **≥1280px**: Side-by-side (70/30 split)
- **1024–1279px**: Side-by-side (60/40 split)
- **768–1023px**: Demo screen full-width on top, conversation panel as a slide-up drawer from bottom (40% height, expandable)
- **<768px**: Demo screen full-width, conversation as a floating overlay button (bottom-right) that opens a full-screen chat panel. Demo screen blurs behind it.

### Admin Console responsive rules:
- **≥1024px**: Sidebar + content
- **768–1023px**: Collapsed sidebar (icons only) + content
- **<768px**: No sidebar, top navigation bar, full-width content

---

## Accessibility

- All interactive elements must have visible focus states (2px amber outline, 2px offset)
- Color contrast: WCAG AA minimum (4.5:1 for body text, 3:1 for large text)
- Keyboard navigation: Full tab support through conversation and controls
- Screen reader: Aria labels on all non-text interactive elements
- Chat messages: Use `role="log"` and `aria-live="polite"` for new messages
- Demo screen: Provide alt text: "Live product demo — [current page being shown]"

---

## Tech Stack Requirements

- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS with custom theme configuration matching above tokens
- **Components**: shadcn/ui as base, heavily customized to match our design system
- **Icons**: Lucide React (consistent, clean line icons)
- **Animations**: Framer Motion for React animations, CSS transitions for simple states
- **Font loading**: Use `next/font` for Satoshi (from Fontshare) and Instrument Sans (Google Fonts)
- **State**: Zustand for client state, React Query for server state
- **WebSocket**: Socket.io client for real-time chat and agent status

---

## Pages to Build

### Demo Stage (Buyer Side)
1. **`/demo/[session-id]`** — The main demo experience. Split-panel layout. Browser stream + conversation. This is the ONLY page prospects see. It must be perfect.
2. **`/demo/[session-id]/ended`** — Post-session page. Summary of what was covered, CTA to book a real call or sign up.

### Admin Console (Owner Side)
3. **`/admin`** — Dashboard. Quick stats: total sessions, avg duration, most-asked features. Keep it minimal — 3-4 metrics, not a data overload.
4. **`/admin/products`** — Product management. List of configured products. Each product is a card showing name, status (active/setup), session count.
5. **`/admin/products/[id]/setup`** — Product setup wizard. Step-by-step: (1) Enter product URL + name, (2) Paste help docs URLs, (3) Upload walkthrough video or paste YouTube link, (4) Add FAQ/knowledge base, (5) Configure agent personality & greeting. Each step is a section on a single scrollable page (not a multi-step wizard with next/back — that's slow).
6. **`/admin/products/[id]/knowledge`** — Knowledge base viewer. See what the agent "knows" — searchable list of ingested chunks, with source attribution (which doc/video it came from). Ability to add, edit, or delete knowledge entries manually.
7. **`/admin/products/[id]/customize`** — Agent customization. Set greeting message, agent name, personality tone (professional/friendly/technical), suggested questions, and human handoff settings (email/calendar link for escalation).
8. **`/admin/sessions`** — Session history table. Columns: Date, Duration, Questions Asked, Features Shown, Handoff Requested (Y/N). Click a row to see the full conversation transcript.
9. **`/admin/sessions/[id]`** — Session detail. Full conversation transcript on the left, session recording/replay on the right (for now, just the transcript — recording is a future feature).
10. **`/admin/embed`** — Embed & share page. Get the shareable demo link. Copy embed code for widget mode (future). Preview what the prospect will see.
11. **`/admin/settings`** — Account settings. Profile, API keys, billing (placeholder for now).

---

## What "Done" Looks Like

When a co-founder or investor sees this, they should feel:
- "This looks like a real product, not a hackathon project"
- "The demo experience is seamless — I forgot I was talking to an AI"
- "The admin side feels as fast and clean as Notion or Linear"
- "This team has taste"

The UI should be the silent proof that this product was built by someone who deeply understands both product design and the problem they're solving.

---

## Anti-Patterns to Avoid

1. **No gradient backgrounds** on surfaces (gradients only in micro-accents like the shimmer effect)
2. **No card shadows by default** — depth comes from background color differences, not shadows
3. **No emoji in the UI** (the agent can use them in messages if personality is set to "friendly", but the UI itself never uses them)
4. **No skeleton avatars** or generic user/bot icons
5. **No "Powered by" badges** in the demo experience — it breaks the immersion
6. **No confirmation modals for non-destructive actions** — use undo toasts instead
7. **No pagination** — use infinite scroll or "load more" for lists
8. **No color other than amber as the primary accent** — the restraint is the brand
9. **No sidebar in the demo stage** — EVER. The conversation is the only navigation.
10. **No tooltips that block content** — use inline help text or expandable sections

---

## File Structure

```
src/
├── app/
│   ├── demo/
│   │   └── [sessionId]/
│   │       ├── page.tsx          // Main demo experience
│   │       └── ended/
│   │           └── page.tsx      // Post-session page
│   ├── admin/
│   │   ├── page.tsx              // Dashboard
│   │   ├── products/
│   │   │   ├── page.tsx          // Product list
│   │   │   └── [id]/
│   │   │       ├── setup/
│   │   │       │   └── page.tsx  // Product setup
│   │   │       ├── knowledge/
│   │   │       │   └── page.tsx  // Knowledge base
│   │   │       └── customize/
│   │   │           └── page.tsx  // Agent customization
│   │   ├── sessions/
│   │   │   ├── page.tsx          // Session history
│   │   │   └── [id]/
│   │   │       └── page.tsx      // Session detail
│   │   ├── embed/
│   │   │   └── page.tsx          // Embed & share
│   │   └── settings/
│   │       └── page.tsx          // Account settings
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                       // shadcn/ui base components (customized)
│   ├── demo/                     // Demo stage components
│   │   ├── DemoScreen.tsx        // Browser stream iframe wrapper
│   │   ├── ConversationPanel.tsx // Chat panel
│   │   ├── AgentMessage.tsx      // Agent message with amber accent
│   │   ├── UserMessage.tsx       // User message
│   │   ├── ThinkingIndicator.tsx // Shimmer line
│   │   ├── NavigationPill.tsx    // "Navigating..." pill
│   │   ├── SuggestedQuestions.tsx // Contextual question pills
│   │   ├── ContextBar.tsx        // Breadcrumb of current demo location
│   │   └── ChatInput.tsx         // Message input with rotating placeholder
│   ├── admin/                    // Admin console components
│   │   ├── Sidebar.tsx
│   │   ├── ProductCard.tsx
│   │   ├── SessionTable.tsx
│   │   ├── KnowledgeList.tsx
│   │   ├── SetupForm.tsx
│   │   └── StatsCard.tsx
│   └── shared/                   // Shared components
│       ├── Logo.tsx
│       ├── Toast.tsx
│       └── EmptyState.tsx
├── lib/
│   ├── theme.ts                  // Design tokens as JS objects
│   ├── socket.ts                 // WebSocket client
│   └── stores/                   // Zustand stores
│       ├── demo-store.ts         // Demo session state
│       └── admin-store.ts        // Admin state
└── styles/
    └── fonts.ts                  // Font configuration
```

---

## Priority Order for Building

Build in this exact order:

1. **Design system foundation**: globals.css with all tokens, Tailwind config, font loading, shadcn/ui setup with customization
2. **Demo Stage — main page**: The `/demo/[sessionId]` page with the split-panel layout, hardcoded mock messages to nail the visual design
3. **Conversation components**: AgentMessage, UserMessage, ThinkingIndicator, NavigationPill, ChatInput, SuggestedQuestions — with all animations

---

## Current Implementation Mapping

- Buyer-side live demo stage: `src/app/meet/[token]/page.tsx`
- Shared live meeting API client: `src/lib/api-v2.ts`
- Live meeting types: `src/types/v2.ts`
- Design tokens and shared stage controls: `src/app/globals.css`
- App font and metadata wiring: `src/app/layout.tsx`

### Current Behavior Contract

- The live browser stage is the dominant surface.
- The conversation panel is the secondary rail with pinned input and assist controls.
- Voice, browser video, transcript, and runtime controls share the same meeting session.
- Direct browser actions are attempted first through the live browser agent.
- Structured recipes remain as fallback accelerators when direct exploration is not reliable.
4. **DemoScreen component**: The iframe wrapper with loading state and warm glow border
5. **Admin layout**: Sidebar + content area shell
6. **Admin dashboard**: Simple stats page
7. **Product setup page**: The single-scroll configuration form
8. **Knowledge base page**: Searchable list view
9. **Session history + detail pages**: Table + transcript view
10. **Embed & share page**: Link generation + preview
11. **Post-session page**: Summary + CTA
12. **Responsive adaptations**: Mobile/tablet layouts for all pages
13. **Polish pass**: Animation timing, transition smoothness, edge cases

Start with step 1 and 2 now. Build them to production quality before moving to step 3.
