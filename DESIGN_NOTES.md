# AI Lead Dashboard — design notes

A single-page prototype (`index.html`) demonstrating the Lead Dashboard + Lead Detail experience. Open the file directly in a browser — no build step.

## What the user is trying to do

1. Scan incoming leads and tell the urgent ones from the rest at a glance.
2. Trust the AI's classification enough to act on it (so the "why" must be visible, not hidden behind an info-icon).
3. Take the next action (reply, qualify, book a call) without losing context.

## Information hierarchy

**Dashboard.** Three layers, top to bottom:
- **Pulse strip** — 4 KPI cards (new today, hot needing reply, response time, conversion). Answers "what should I care about right now?"
- **Filter strip** — tabbed temperature filter (All / Hot / Warm / Cold) is the primary axis because that's the AI's main job. Source / owner / time are secondary dropdowns.
- **Lead table** — one row per lead. Each row shows: identity, company, **AI insight (badge + score bar in one cell)**, source, last activity, quick actions. Sorted by AI score by default.

The temperature badge and the score bar share a single cell so the reader gets the categorical signal and the magnitude in one glance — the bar is the "is 92 really hotter than 87?" tiebreaker.

**Lead detail.** 2/3 + 1/3 split:
- **Left (context)** — identity header, AI insight panel (the "why"), then activity timeline. This is the "read" column.
- **Right (act)** — score widget, key facts, AI-drafted reply with tone toggle. This is the "do" column. Putting the composer in the sidebar means a user can read the activity feed and reply without scrolling.

## How AI is surfaced

AI output is treated as a **first-class citizen, not a tooltip**:
- A labeled "AI insight" panel sits above the activity feed with a plain-English summary, 4 signal chips (Pricing views, Reply latency, Seniority, ICP fit) and an "Updated 4 min ago" stamp.
- Score is shown as a number, a progress bar, and a one-line decomposition (`+22 fit · +35 intent · +18 engagement · +17 timing`) so users learn the model's mental shape over time.
- Suggested next actions are framed as buttons, not advice — clicking them is the path of least resistance.
- AI-generated copy (the reply draft) is always labeled and editable, with a tone switcher and a regenerate button.

## Choices made to keep it simple

- **No multi-color heatmaps.** Three temperature colors only (red/amber/blue) and one brand accent. Everything else is neutral.
- **One typography scale** (Inter, 4 sizes).
- **Tabs over sidebars** for filtering — fewer clicks to switch the most important axis.
- **Inline quick actions** on hover so the table stays scannable when idle.
- **Keyboard**: `/` focuses search, `Esc` returns from detail to list. Cheap to add, big payoff for power users.

## What's intentionally left out

- Multi-select bulk actions toolbar (designed for, not built — checkbox column is in place).
- Pipeline/board view (sidebar item exists, screen does not).
- Notes / files / tasks tabs on the detail page (tabs visible, content stubbed).
- Real-time updates and notifications.

These are scope-honest cuts, not oversights — the goal was the spine of the experience, not every leaf.

## File

- `index.html` — fully self-contained (Tailwind via CDN, vanilla JS, mock data inline). Click any row to open the detail view.
