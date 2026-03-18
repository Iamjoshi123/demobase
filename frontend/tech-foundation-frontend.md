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