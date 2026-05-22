# AI Lead Dashboard — Lume

Single-page prototype implementing the design handoff from `claude.ai/design`. Open `index.html` in any browser, no build step.

## Files

- `index.html` — entry point. Loads React 18 + Babel standalone and the three scripts below.
- `data.js` — shared lead data and owner colors. `window.LEADS`, `window.OWNER_COLORS`.
- `app-shell.jsx` — icons, app state hooks, sidebar, top bar, sparkline, KPI strip, page header (incl. AI strip), toolbar, popover.
- `app.jsx` — lead table, lead drawer (with AI insight card, quick actions, tabs), modals, app root.
- `styles.css` — full design system: tokens (colors, ink, hairlines, accent, temperature, elevation, radii), components, animations.

## Experience

**Dashboard**
- Sidebar with brand mark, ⌘K search, primary nav (Inbox / Leads / Pipeline / Sequences / Reports), saved views (Today / Hot / Stalled > 7d / Assigned to me) with live counts, and an account chip.
- Top bar with breadcrumbs (Workspace / Leads), search, theme/notification icons. Glassy backdrop blur.
- Page header: large title with iris accent dot, meta counts, "Ask Lume" (AI) and "New lead" buttons.
- **KPI strip**: Hot leads, Hot pipeline ($k), Median reply (m), Demo → won (%) — each with a smooth Catmull-Rom sparkline, gradient area fill, end-dot with halo, signed delta, and sub-label.
- **AI strip** under the KPIs: one-line, iridescent accent rule, plain-English priority brief with confidence stamp and "Open brief" CTA.
- Toolbar: segment chips (Today / Hot / Mine / Stalled / All), add-filter, sort, density toggle (comfy / compact).
- **Lead table**: avatar + name + unread pip + sub (title · company), score cell with per-row sparkline tinted by temp, stage pill (color-coded), owner avatar, last activity, top AI signal, and row hover reveals a More menu.

**Lead drawer** (slides in from the right)
- Header: large avatar, name + stage pill, title · company, meta row (employees, location, last activity, source).
- **AI insight card**: large tabular score colored by temperature, grade + signal count, top signal, plain-English summary, and a "Next action" recommendation in a nested surface.
- Quick actions: Reply (primary), Schedule, Qualify, Assign, Snooze.
- Tabs: Overview (score breakdown + intent chips), Messages (thread + AI-drafted composer with Direct / Warm / Curious tone toggles and confidence stamp), Activity (timeline), Notes (with persistent sticky note + composer).

**Interactions**
- ⌘K / Ctrl+K focuses search.
- Click any row to open the drawer; J/K (or arrow keys) navigate prev/next; Esc closes.
- Add filters (Stage, Score, Owner, Source, Temp), sort by Score / Activity / Name / Company.
- Toggle density between comfortable and compact.
- "Ask Lume" modal returns a ranked AI plan and a "Show these leads" CTA that filters the list to Hot.
- Quick actions update state (qualify advances stage; assign reassigns owner; reply/snooze produce toasts).

## Design system highlights

- **Type**: Geist sans, Geist Mono for IDs, scores, and confidence stamps.
- **Color**: warm off-white (`#fafaf9`) bg, near-monochrome ink scale, hairline borders. One indigo accent (Radix iris `#5b5bd6`) reserved for AI moments. Temperature: burnt orange `#c2410c` (hot), amber `#a16207` (warm), blue `#2563eb` (cold).
- **Shadows**: dedicated `--shadow-ai` (soft iris glow) for AI surfaces; otherwise minimal `xs / sm / md / lg`.
- **Motion**: 80ms ease for hover, 240ms cubic-bezier for the drawer, shimmer keyframes for AI loading states.
- **Sparklines**: smooth Catmull-Rom-style Bézier with vertical gradient fill and a layered end-dot (outer halo + colored core + inner white pip).
