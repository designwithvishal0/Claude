// Lume — minimalist SaaS lead dashboard
const { useState, useEffect, useRef, useMemo } = React;

// ─── Icons (lucide-style, 1.5px stroke) ──────────────────────────
const I = {
  Inbox:    (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>,
  Users:    (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  Pipe:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="3" y="3" width="6" height="18" rx="1"/><rect x="11" y="3" width="6" height="12" rx="1"/><rect x="19" y="3" width="2" height="6" rx="1"/></svg>,
  Mail:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 5L2 7"/></svg>,
  Bar:      (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 3v18h18"/><path d="M7 14l3-3 4 4 5-7"/></svg>,
  Search:   (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>,
  Bell:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>,
  Cmd:      (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 6h7M8.5 18h7M6 8.5v7M18 8.5v7"/></svg>,
  Sun:      (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="12" cy="12" r="4"/><path d="M12 3v1M12 20v1M3 12h1M20 12h1M5.6 5.6l.7.7M17.7 17.7l.7.7M5.6 18.4l.7-.7M17.7 6.3l.7-.7"/></svg>,
  Plus:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 5v14M5 12h14"/></svg>,
  X:        (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M18 6 6 18M6 6l12 12"/></svg>,
  Spark:    (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 3v3M12 18v3M5 12H2M22 12h-3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></svg>,
  Sort:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 6h14M3 12h10M3 18h6"/></svg>,
  Filter:   (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 4h18l-7 9v6l-4 2v-8L3 4z"/></svg>,
  Rows:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/></svg>,
  Compact:  (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 6h18M3 12h18M3 18h18"/></svg>,
  More:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="6" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18" cy="12" r="1.2"/></svg>,
  Up:       (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="m18 15-6-6-6 6"/></svg>,
  Down:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="m6 9 6 6 6-6"/></svg>,
  Right:    (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="m9 18 6-6-6-6"/></svg>,
  Check:    (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M20 6 9 17l-5-5"/></svg>,
  Cal:      (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>,
  Clock:    (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>,
  Pin:      (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 21V12M5 9V4h14v5l-3 3v3l3 3H5l3-3v-3z"/></svg>,
  Convert:  (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M17 3 21 7l-4 4M7 21l-4-4 4-4"/><path d="M3 7h14M21 17H7"/></svg>,
  Assign:   (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="9" cy="8" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M19 8v6M16 11h6"/></svg>,
  Reply:    (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M9 17 4 12l5-5"/><path d="M4 12h11a5 5 0 0 1 5 5v3"/></svg>,
  Snooze:   (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M19.5 14a7.5 7.5 0 0 1-9.5 8.5A7.5 7.5 0 1 1 19.5 14z"/></svg>,
  Map:      (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 1 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>,
  Bldg:     (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 21V8l9-5 9 5v13"/><path d="M9 21v-6h6v6M9 11h.01M15 11h.01"/></svg>,
  Doc:      (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>,
};

// ─── App state ───────────────────────────────────────────────────
function useAppState() {
  const [leads, setLeads] = useState(() => window.LEADS.map(l => ({ ...l, drafts: makeDrafts(l), messages: makeMessages(l), timeline: makeTimeline(l) })));
  const [toasts, setToasts] = useState([]);
  const [modal, setModal] = useState(null);
  const tid = useRef(0);

  const updateLead = (id, patch) => setLeads(ls => ls.map(l => l.id === id ? { ...l, ...patch } : l));
  const markRead = (id) => updateLead(id, { unread: 0 });
  const appendActivity = (id, ev) => setLeads(ls => ls.map(l => l.id === id ? { ...l, timeline: [{ t: "just now", ...ev }, ...l.timeline] } : l));

  const toast = (message, opts = {}) => {
    const id = ++tid.current;
    setToasts(ts => [...ts, { id, message, ...opts }]);
    setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), opts.duration || 3800);
  };
  const dismiss = (id) => setToasts(ts => ts.filter(t => t.id !== id));

  return { leads, updateLead, markRead, appendActivity, toast, dismiss, toasts, modal, setModal };
}

function makeDrafts(l) {
  const first = l.name.split(" ")[0];
  return {
    direct: `Hi ${first},\n\nCongrats on the Series C — that's huge. Saw you booked time on our calendar; before we meet, two quick questions so I can tailor the demo:\n\n1) How are you handling SLA reporting today?\n2) Who else on your team would benefit from being on the call?\n\nLooking forward,\nSam`,
    warm: `Hi ${first},\n\nLovely to be connected. Genuinely impressed by what Northwind is building.\n\nLet me know what would be most useful to cover. Happy to keep it brief.\n\n— Sam`,
    curious: `Hi ${first},\n\nA few quick questions so I send the right thing first:\n\n• What's prompting the search now?\n• What does "great" look like in 90 days?\n• Any deal-breakers we should know up front?\n\n— Sam`,
  };
}
function makeMessages(l) {
  if (l.id === "L-2918") return [
    { dir: "in", who: "Priya Raghavan · priya@northwindlabs.com", when: "12 min ago", text: "Hi Sam — booked a slot for Thursday. Can you bring whoever owns SLA / SOC2 to the call? My CTO wants to be in." },
  ];
  if (l.id === "L-2914") return [
    { dir: "in", who: "Arjun Kapoor · arjun@halcyon.io", when: "2 h ago", text: "Forwarded your pricing breakdown to our CFO. He likes the per-seat option but wants to understand annual commit. Can you send a one-pager that's procurement-friendly?" },
  ];
  return [];
}
function makeTimeline(l) {
  const base = [
    { w: "12 min", t: "Booked demo from /pricing", k: "cal" },
    { w: "2 h",    t: "Replied: 'CTO wants to be on call'", k: "mail" },
    { w: "1 d",    t: "Score recomputed → " + l.score + " (+8)", k: "ai" },
    { w: "2 d",    t: "Joined trial workspace", k: "doc" },
    { w: "4 d",    t: "Visited /pricing twice", k: "doc" },
  ];
  return base;
}

// ─── Segments / filter ───────────────────────────────────────────
const SEGMENTS = [
  { id: "today",   label: "Today",   ai: true },
  { id: "hot",     label: "Hot",     ai: true },
  { id: "mine",    label: "Mine" },
  { id: "stalled", label: "Stalled" },
  { id: "all",     label: "All" },
];
function inSeg(l, seg) {
  if (seg === "all")     return true;
  if (seg === "mine")    return l.owner === "You";
  if (seg === "hot")     return l.temp === "hot";
  if (seg === "stalled") return l.lastActivityRaw > 4000 && l.temp !== "cold";
  if (seg === "today")   return l.lastActivityRaw < 1500;
  return true;
}

const STAGE_NEXT = ["New", "Engaged", "Qualifying", "Opportunity", "Won"];
const nextStage = (s) => STAGE_NEXT[Math.min(STAGE_NEXT.length - 1, Math.max(0, STAGE_NEXT.indexOf(s) + 1))] || "Engaged";

const TEMP_COLOR = { hot: "#c2410c", warm: "#a16207", cold: "#2563eb" };
const TEMP_GRADE = { hot: "Hot", warm: "Warm", cold: "Cold" };

// ─── Sidebar ─────────────────────────────────────────────────────
function Sidebar({ counts, activeSeg, setActiveSeg }) {
  return (
    <aside className="side">
      <div className="side-brand">
        <div className="mark">L</div>
        <div className="nm">Lume</div>
        <span className="car">▾</span>
      </div>
      <div className="side-search" onClick={() => document.querySelector(".top-search input")?.focus()}>
        <I.Search width="13" height="13" />
        <span>Search</span>
        <span className="grow" />
        <kbd>⌘K</kbd>
      </div>

      <div className="side-item"><span className="ic"><I.Inbox width="14" height="14" /></span><span>Inbox</span><span className="n tnum">12</span></div>
      <div className="side-item on"><span className="ic"><I.Users width="14" height="14" /></span><span>Leads</span><span className="dot" title="Lume has updates" /></div>
      <div className="side-item"><span className="ic"><I.Pipe width="14" height="14" /></span><span>Pipeline</span></div>
      <div className="side-item"><span className="ic"><I.Mail width="14" height="14" /></span><span>Sequences</span></div>
      <div className="side-item"><span className="ic"><I.Bar width="14" height="14" /></span><span>Reports</span></div>

      <div className="side-h">Views</div>
      <div className={`side-item ${activeSeg === "today"   ? "on" : ""}`} onClick={() => setActiveSeg("today")}>
        <span className="ic"><I.Spark width="13" height="13" /></span>
        <span>Today</span>
        <span className="n tnum">{counts.today}</span>
      </div>
      <div className={`side-item ${activeSeg === "hot"     ? "on" : ""}`} onClick={() => setActiveSeg("hot")}>
        <span className="ic" style={{ color: "var(--hot)" }}>●</span>
        <span>Hot</span>
        <span className="n tnum">{counts.hot}</span>
      </div>
      <div className={`side-item ${activeSeg === "stalled" ? "on" : ""}`} onClick={() => setActiveSeg("stalled")}>
        <span className="ic" style={{ color: "var(--warm)" }}>●</span>
        <span>Stalled &gt; 7d</span>
        <span className="n tnum">{counts.stalled}</span>
      </div>
      <div className={`side-item ${activeSeg === "mine"    ? "on" : ""}`} onClick={() => setActiveSeg("mine")}>
        <span className="ic"><I.Pin width="13" height="13" /></span>
        <span>Assigned to me</span>
        <span className="n tnum">{counts.mine}</span>
      </div>

      <div className="side-me">
        <div className="av you">SK</div>
        <div className="who"><div className="nm">Sam Kovacs</div><div className="org">Acme · Pro</div></div>
        <span className="car">▾</span>
      </div>
    </aside>
  );
}

// ─── Top bar ─────────────────────────────────────────────────────
function TopBar({ search, setSearch }) {
  const ref = useRef(null);
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); ref.current?.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <div className="top">
      <div className="crumbs">
        <span>Workspace</span>
        <span className="sep">/</span>
        <span className="here">Leads</span>
      </div>
      <div className="grow" />
      <div className="top-search" style={{ display: "flex", alignItems: "center", gap: 8, height: 28, padding: "0 10px", border: "1px solid var(--line)", borderRadius: 8, width: 260, background: "var(--bg)", color: "var(--muted)" }}>
        <I.Search width="13" height="13" />
        <input
          ref={ref}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search leads, signals…"
          style={{ flex: 1, border: "none", outline: "none", background: "transparent", font: "inherit", fontSize: 12.5, color: "var(--ink)" }}
        />
        {!search && <kbd style={{ fontFamily: "inherit", fontSize: 10.5, color: "var(--muted-2)", border: "1px solid var(--line)", padding: "1px 5px", borderRadius: 4 }}>⌘K</kbd>}
        {search && <button className="iconbtn" style={{ width: 20, height: 20 }} onClick={() => setSearch("")}><I.X width="11" height="11" /></button>}
      </div>
      <button className="iconbtn" title="Theme"><I.Sun width="14" height="14" /></button>
      <button className="iconbtn" title="Notifications"><I.Bell width="14" height="14" /></button>
    </div>
  );
}

// ─── Sparkline (smooth + gradient fill) ─────────────────────────
function smoothPath(pts) {
  if (pts.length < 2) return "";
  let d = `M${pts[0][0].toFixed(2)},${pts[0][1].toFixed(2)}`;
  const t = 0.22;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1x = p1[0] + (p2[0] - p0[0]) * t;
    const c1y = p1[1] + (p2[1] - p0[1]) * t;
    const c2x = p2[0] - (p3[0] - p1[0]) * t;
    const c2y = p2[1] - (p3[1] - p1[1]) * t;
    d += ` C${c1x.toFixed(2)},${c1y.toFixed(2)} ${c2x.toFixed(2)},${c2y.toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)}`;
  }
  return d;
}

let __sparkN = 0;
function Sparkline({
  data, width = 56, height = 18,
  withDot = true, fill = true,
  padTop = 3, padBot = 3, padX = 1,
  smooth = true, strokeWidth = 1.5,
}) {
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const dx = (width - padX * 2) / (data.length - 1);
  const points = data.map((v, i) => [
    padX + i * dx,
    height - ((v - min) / range) * (height - padTop - padBot) - padBot,
  ]);
  const line = smooth
    ? smoothPath(points)
    : points.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(" ");
  const area = `${line} L${(width - padX).toFixed(2)},${height} L${padX.toFixed(2)},${height} Z`;
  const last = points[points.length - 1];
  const first = points[0];
  const gid = "sg" + (++__sparkN);
  return (
    <svg className="spark" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="currentColor" stopOpacity="0.32" />
          <stop offset="60%"  stopColor="currentColor" stopOpacity="0.06" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${gid})`} />}
      <path d={line} fill="none" stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round" strokeLinejoin="round"
            vectorEffect="non-scaling-stroke" />
      {withDot && (
        <g>
          <circle cx={first[0]} cy={first[1]} r="1.4" fill="currentColor" opacity="0.30" />
          <circle cx={last[0]}  cy={last[1]}  r="3.6" fill="currentColor" opacity="0.16" />
          <circle cx={last[0]}  cy={last[1]}  r="2.0" fill="currentColor" />
          <circle cx={last[0]}  cy={last[1]}  r="0.9" fill="white" />
        </g>
      )}
    </svg>
  );
}

// ─── KPI strip ─────────────────────────────────────────────────
const KPIS = [
  {
    id: "hot", tone: "hot", lab: "Hot leads", val: "7", unit: "", delta: "+3", dir: "up",
    sub: "3 added overnight",
    spark: [3, 4, 3, 5, 4, 6, 5, 7, 6, 7],
  },
  {
    id: "pipe", tone: "ink", lab: "Hot pipeline", val: "$486", unit: "k", delta: "+$92k", dir: "up",
    sub: "vs $394k Mon",
    spark: [392, 401, 410, 408, 422, 440, 448, 463, 472, 486],
  },
  {
    id: "reply", tone: "cold", lab: "Median reply", val: "12", unit: "m", delta: "−4m", dir: "up",
    sub: "faster than goal",
    spark: [22, 19, 21, 18, 17, 16, 18, 15, 14, 12],
  },
  {
    id: "conv", tone: "acc", lab: "Demo → won", val: "34", unit: "%", delta: "+2pt", dir: "up",
    sub: "30-day rolling",
    spark: [28, 29, 30, 31, 30, 32, 33, 32, 34, 34],
    aiLab: true,
  },
];

function KpiStrip({ active, onPick }) {
  return (
    <div className="kpis">
      {KPIS.map(k => (
        <div key={k.id} className={`kpi ${k.tone} ${active === k.id ? "active" : ""}`} onClick={() => onPick && onPick(k.id)}>
          <div className="lab">
            {k.aiLab && <span className="ic ai"><I.Spark width="11" height="11" /></span>}
            {k.lab}
            <span className="grow" style={{ flex: 1 }} />
          </div>
          <div className="row">
            <div className="val tnum">{k.val}<small>{k.unit}</small></div>
            <div className={`delta tnum ${k.dir === "up" ? "up" : "down"}`}>{k.delta}</div>
          </div>
          <Sparkline data={k.spark} width={240} height={36} strokeWidth={1.75} fill />
          <div className="sub">{k.sub}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Page header + AI strip ──────────────────────────────────────
function PageHeader({ counts, onAskAi, onNew, onSeg }) {
  return (
    <div className="head">
      <div className="head-row">
        <h1 className="h1"><span className="accent-dot" />Leads</h1>
        <span className="head-meta tnum">{counts.all} total · {counts.mine} yours · 7 hot</span>
        <span className="grow" />
        <button className="btn ai" onClick={onAskAi}><span className="ic"><I.Spark width="13" height="13" /></span>Ask Lume</button>
        <button className="btn primary" onClick={onNew}><I.Plus width="13" height="13" /> New lead</button>
      </div>

      <KpiStrip />

      <div className="ai-strip" onClick={() => onSeg("hot")} style={{ cursor: "pointer" }}>
        <span className="ic"><I.Spark width="13" height="13" /></span>
        <span className="grow">
          <b className="tnum">{counts.hot}</b> leads need attention today.{" "}
          <span style={{ color: "var(--muted)" }}>Priya booked a demo 12m ago. Arjun forwarded your CFO note. Vikram replied to Ada's referral.</span>
        </span>
        <span className="conf">conf · 92%</span>
        <button className="btn sm ghost" onClick={(e) => { e.stopPropagation(); onAskAi(); }}>Open brief <I.Right width="11" height="11" /></button>
      </div>
    </div>
  );
}

// ─── Toolbar (segment chips + filters + sort + density) ──────────
function Toolbar({ activeSeg, setActiveSeg, counts, density, setDensity, sort, setSort, filters, setFilters }) {
  const [filterAnchor, setFilterAnchor] = useState(null);
  const [sortAnchor, setSortAnchor] = useState(null);
  const sortLabel = ({ score: "Score", lastActivityRaw: "Activity", name: "Name", company: "Company" })[sort.id];
  return (
    <div className="tools">
      {SEGMENTS.map(s => (
        <button
          key={s.id}
          className={`chip ${activeSeg === s.id ? "on" : ""}`}
          onClick={() => setActiveSeg(s.id)}
        >
          {s.ai && activeSeg !== s.id && <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--accent)" }} />}
          {s.label}
          <span className="n">{counts[s.id]}</span>
        </button>
      ))}

      {filters.map((f, i) => (
        <button key={i} className="chip" onClick={() => setFilters(filters.filter((_, j) => j !== i))}>
          <span style={{ color: "var(--muted)" }}>{f.field}</span> {f.op} <b>{f.value}</b>
          <I.X width="10" height="10" className="x" />
        </button>
      ))}
      <button className="chip dashed" onClick={(e) => setFilterAnchor(e.currentTarget)}>
        <I.Plus width="11" height="11" /> Filter
      </button>
      <button className="chip dashed" onClick={(e) => setSortAnchor(e.currentTarget)}>
        <I.Sort width="12" height="12" /> {sortLabel} {sort.dir === "desc" ? "↓" : "↑"}
      </button>

      <span className="grow" />

      <div className="toggle">
        <button className={density === "comfy" ? "on" : ""} onClick={() => setDensity("comfy")} title="Comfortable"><I.Rows width="12" height="12" /></button>
        <button className={density === "compact" ? "on" : ""} onClick={() => setDensity("compact")} title="Compact"><I.Compact width="12" height="12" /></button>
      </div>

      {filterAnchor && (
        <Popover anchor={filterAnchor} onClose={() => setFilterAnchor(null)}>
          <div className="h">Add filter</div>
          {[
            { field: "Stage",  op: "is", value: "Engaged" },
            { field: "Score",  op: "≥",  value: "80" },
            { field: "Owner",  op: "is", value: "You" },
            { field: "Source", op: "is", value: "Demo request" },
            { field: "Temp",   op: "is", value: "hot" },
          ].map(p => (
            <div key={p.field} className="mi" onClick={() => { setFilters([...filters, p]); setFilterAnchor(null); }}>
              <span className="ic"><I.Filter width="12" height="12" /></span>
              <span>{p.field}</span>
              <span className="sub">{p.op} {p.value}</span>
            </div>
          ))}
        </Popover>
      )}

      {sortAnchor && (
        <Popover anchor={sortAnchor} onClose={() => setSortAnchor(null)}>
          <div className="h">Sort by</div>
          {[
            { id: "score", label: "AI score" },
            { id: "lastActivityRaw", label: "Last activity" },
            { id: "name", label: "Name" },
            { id: "company", label: "Company" },
          ].map(s => (
            <div key={s.id} className="mi" onClick={() => { setSort({ id: s.id, dir: sort.id === s.id && sort.dir === "desc" ? "asc" : "desc" }); setSortAnchor(null); }}>
              {sort.id === s.id ? <I.Check width="12" height="12" /> : <span style={{ width: 12 }} />}
              <span>{s.label}</span>
            </div>
          ))}
        </Popover>
      )}
    </div>
  );
}

// ─── Popover ─────────────────────────────────────────────────────
function Popover({ anchor, onClose, children, align = "left" }) {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const ref = useRef(null);
  useEffect(() => {
    if (!anchor) return;
    const r = anchor.getBoundingClientRect();
    setPos({ x: align === "left" ? r.left : r.right, y: r.bottom + 4 });
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target) && !anchor.contains(e.target)) onClose(); };
    const onEsc = (e) => { if (e.key === "Escape") onClose(); };
    setTimeout(() => document.addEventListener("mousedown", onDoc), 0);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onEsc); };
  }, [anchor]);
  const style = { left: align === "left" ? pos.x : "auto", right: align === "right" ? window.innerWidth - pos.x : "auto", top: pos.y };
  return <div ref={ref} className="pop" style={style}>{children}</div>;
}

Object.assign(window, {
  I, useAppState, SEGMENTS, inSeg, nextStage, TEMP_COLOR, TEMP_GRADE,
  Sidebar, TopBar, PageHeader, Toolbar, Popover, Sparkline,
});
