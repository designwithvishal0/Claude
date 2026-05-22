// Lume — table, drawer, modals, main app
const { useState: useS, useEffect: useE, useRef: useR, useMemo: useM } = React;
// Pull cross-file globals (consts from app-shell.jsx don't auto-propagate)
const { I, SEGMENTS, TEMP_COLOR, TEMP_GRADE, Sparkline } = window;

// Deterministic score history per lead — a 10-point trajectory ending at current score
function scoreHistory(lead) {
  const target = lead.score;
  const seed = (lead.id.charCodeAt(2) * 13 + lead.id.charCodeAt(3) * 7) % 17;
  const drift = lead.temp === "hot" ? 14 : lead.temp === "warm" ? 6 : -4;
  const start = Math.max(20, target - drift);
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const t = i / 9;
    const noise = ((seed + i * 5) % 9) - 4;
    pts.push(Math.round(start + (target - start) * t + noise * 0.8));
  }
  pts[9] = target;
  return pts;
}

// ─── Table ───────────────────────────────────────────────────────
function LeadTable({ leads, selectedId, onSelect, density, sort, setSort, onAction }) {
  if (leads.length === 0) {
    return (
      <div className="tbl-wrap">
        <div className="tbl-empty">
          <div className="big">No leads match this view.</div>
          <div>Try clearing filters or switch back to All.</div>
        </div>
      </div>
    );
  }
  const th = (id, label, opts = {}) => {
    const active = sort.id === id;
    return (
      <th className={opts.num ? "num" : ""}>
        <button
          onClick={() => setSort({ id, dir: active && sort.dir === "desc" ? "asc" : "desc" })}
          style={{ background: "none", border: "none", font: "inherit", color: active ? "var(--ink)" : "var(--muted)", display: "inline-flex", alignItems: "center", gap: 4, padding: 0, cursor: "pointer", fontWeight: 500, fontSize: 11.5, letterSpacing: 0.01 }}
        >
          {label}
          {active && (sort.dir === "desc" ? <I.Down width="11" height="11" /> : <I.Up width="11" height="11" />)}
        </button>
      </th>
    );
  };
  return (
    <div className={`tbl-wrap ${density === "compact" ? "compact" : ""}`}>
      <table className="tbl">
        <thead>
          <tr>
            {th("name",  "Lead")}
            {th("score", "Score", { num: true })}
            <th>Stage</th>
            <th>Owner</th>
            {th("lastActivityRaw", "Last activity")}
            <th>Top signal · Lume</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {leads.map(l => (
            <LeadRow key={l.id} lead={l} selected={l.id === selectedId} onSelect={onSelect} onAction={onAction} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LeadRow({ lead, selected, onSelect, onAction }) {
  const top = lead.signals[0];
  return (
    <tr className={selected ? "sel" : ""} onClick={() => onSelect(lead)}>
      <td>
        <div className="lead-cell">
          <div className={`av ${avatarClass(lead)}`}>{lead.initials}</div>
          <div className="who">
            <div className="nm">
              {lead.name}
              {lead.unread > 0 && <span className="unread-pip">{lead.unread}</span>}
            </div>
            <div className="sub">{lead.title} · {lead.company}</div>
          </div>
        </div>
      </td>
      <td className="num">
        <span className={`score-cell ${lead.temp}`}>
          <Sparkline data={scoreHistory(lead)} width={64} height={22} strokeWidth={1.5} />
          <span className="n">{lead.score}</span>
        </span>
      </td>
      <td>
        <span className="pill" data-s={lead.stage}>
          <span className="dot" />
          {lead.stage}
        </span>
      </td>
      <td>
        <span className="owner">
          <span className={`av sm ${ownerClass(lead.owner)}`}>{window.OWNER_COLORS[lead.owner].init}</span>
          {lead.owner === "You" ? "You" : lead.owner}
        </span>
      </td>
      <td><span className="when">{lead.lastActivity}{lead.unread > 0 && <small>unread</small>}</span></td>
      <td>
        <div className="signal">
          <span className="ic"><I.Spark width="12" height="12" /></span>
          <span className="t">{top?.label}</span>
        </div>
      </td>
      <td style={{ textAlign: "right" }}>
        <button className="iconbtn" onClick={(e) => { e.stopPropagation(); onAction("row-more", lead, e.currentTarget); }}>
          <I.More width="14" height="14" />
        </button>
      </td>
    </tr>
  );
}

function avatarClass(l) {
  const tones = ["", "you", "dani", "alex"];
  return tones[(l.id.charCodeAt(2) + l.id.charCodeAt(3)) % tones.length] || "";
}
function ownerClass(o) {
  return ({ "You": "you", "Dani Park": "dani", "Alex Romano": "alex", "Unassigned": "unassigned" })[o] || "";
}

// ─── Drawer ──────────────────────────────────────────────────────
function Drawer({ lead, onClose, onPrev, onNext, onAction }) {
  const open = !!lead;
  const [tab, setTab] = useS("overview");
  const [draftKind, setDraftKind] = useS("direct");
  useE(() => { if (lead) setTab("overview"); }, [lead?.id]);
  useE(() => {
    const onKey = (e) => {
      if (!open) return;
      if (e.key === "Escape") onClose();
      if (e.key === "j" || e.key === "ArrowDown") onNext();
      if (e.key === "k" || e.key === "ArrowUp")   onPrev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onNext, onPrev, onClose]);

  return (
    <>
      <div className={`scrim ${open ? "open" : ""}`} onClick={onClose} />
      <aside className={`drawer ${open ? "open" : ""}`}>
        {lead && (
          <>
            <div className="dr-top">
              <button className="iconbtn" onClick={onClose}><I.X width="14" height="14" /></button>
              <span className="id mono">{lead.id}</span>
              <span className="grow" />
              <button className="iconbtn" onClick={onPrev} title="Previous (k)"><I.Up width="14" height="14" /></button>
              <button className="iconbtn" onClick={onNext} title="Next (j)"><I.Down width="14" height="14" /></button>
              <button className="iconbtn" onClick={(e) => onAction("more", lead, e.currentTarget)}><I.More width="14" height="14" /></button>
            </div>
            <div className="dr-body">
              <DrawerHead lead={lead} />
              <AiCard lead={lead} />
              <QuickActions lead={lead} onAction={onAction} />

              <div className="dr-tabs">
                {["overview", "messages", "activity", "notes"].map(k => (
                  <button key={k} className={`dr-tab ${tab === k ? "on" : ""}`} onClick={() => setTab(k)}>
                    {k[0].toUpperCase() + k.slice(1)}
                  </button>
                ))}
              </div>

              <div className="tab-body">
                {tab === "overview" && <Overview lead={lead} />}
                {tab === "messages" && <Messages lead={lead} draftKind={draftKind} setDraftKind={setDraftKind} onAction={onAction} />}
                {tab === "activity" && <Activity lead={lead} />}
                {tab === "notes" && <Notes lead={lead} />}
              </div>
            </div>
          </>
        )}
      </aside>
    </>
  );
}

function DrawerHead({ lead }) {
  return (
    <div className="dr-head">
      <div className={`av lg ${avatarClass(lead)}`}>{lead.initials}</div>
      <div className="info">
        <h2 className="nm">
          {lead.name}
          <span className="pill" data-s={lead.stage} style={{ marginLeft: 8, fontSize: 11 }}>
            <span className="dot" />
            {lead.stage}
          </span>
        </h2>
        <div className="sub">{lead.title} at {lead.company}</div>
        <div className="meta">
          <span className="item"><span className="ic"><I.Bldg width="12" height="12" /></span>{lead.employees} ppl</span>
          <span className="item"><span className="ic"><I.Map width="12" height="12" /></span>{lead.location}</span>
          <span className="item"><span className="ic"><I.Clock width="12" height="12" /></span>{lead.lastActivity}</span>
          <span className="item"><span className="ic"><I.Doc width="12" height="12" /></span>via {lead.source}</span>
        </div>
      </div>
    </div>
  );
}

function AiCard({ lead }) {
  return (
    <div className="ai-card">
      <div className="hd">
        <span className="ic"><I.Spark width="13" height="13" /></span>
        <span className="lbl">Lume insight</span>
        <span className="conf">confidence {lead.confidence}%</span>
      </div>
      <div className="score-line">
        <div className="big tnum" style={{ color: TEMP_COLOR[lead.temp] }}>{lead.score}</div>
        <div className="score-meta">
          <div className="g">{TEMP_GRADE[lead.temp]} · {lead.signals.length} signal{lead.signals.length !== 1 ? "s" : ""}</div>
          <div className="why">Top: {lead.signals[0]?.label}</div>
        </div>
      </div>
      <div className="sm">{lead.summary}</div>
      <div className="ai-rec">
        <span className="ic"><I.Spark width="13" height="13" /></span>
        <div>
          <span className="lbl">Next action</span>
          {lead.rec}
        </div>
      </div>
    </div>
  );
}

function QuickActions({ lead, onAction }) {
  return (
    <div className="qa">
      <button className="btn primary" onClick={() => onAction("reply", lead)}><I.Reply width="12" height="12" /> Reply</button>
      <button className="btn" onClick={() => onAction("schedule", lead)}><I.Cal width="12" height="12" /> Schedule</button>
      <button className="btn" onClick={() => onAction("qualify", lead)}><I.Check width="12" height="12" /> Qualify</button>
      <button className="btn" onClick={(e) => onAction("assign", lead, e.currentTarget)}><I.Assign width="12" height="12" /> Assign</button>
      <button className="btn ghost" onClick={() => onAction("snooze", lead)}><I.Snooze width="12" height="12" /> Snooze</button>
    </div>
  );
}

function Overview({ lead }) {
  return (
    <>
      <div className="sec-h">Score breakdown</div>
      <div className="sig-list">
        {lead.signals.map((s, i) => (
          <div className="sig-row" key={i}>
            <span className={`w ${s.weight}`}>{s.weight === "strong" ? "+ Strong" : s.weight === "medium" ? "+ Medium" : "± Weak"}</span>
            <span className="l">{s.label}</span>
            <span className="p tnum">{s.weight === "strong" ? "+18" : s.weight === "medium" ? "+9" : "+3"}</span>
          </div>
        ))}
      </div>
      <div className="sec-h">Intent</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {lead.intent.length === 0 && <span style={{ color: "var(--muted)", fontSize: 12.5 }}>No clear intent signals yet.</span>}
        {lead.intent.map(t => <span key={t} className="chip">{t}</span>)}
      </div>
    </>
  );
}

function Messages({ lead, draftKind, setDraftKind, onAction }) {
  const [draft, setDraft] = useS(lead.drafts[draftKind]);
  useE(() => { setDraft(lead.drafts[draftKind]); }, [lead.id, draftKind]);
  return (
    <>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {lead.messages.length === 0 ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--muted)", border: "1px dashed var(--line)", borderRadius: 8, fontSize: 12.5 }}>
            No replies yet. Be the first to write.
          </div>
        ) : lead.messages.map((m, i) => (
          <div key={i} className={`msg in`}>
            <div className="who">{m.who} · {m.when}</div>
            {m.text}
          </div>
        ))}
      </div>
      <div className="sec-h">Draft <span style={{ color: "var(--accent)", fontWeight: 500 }}>· Lume</span></div>
      <div className="composer">
        <div className="dh">
          <span className="ic"><I.Spark width="12" height="12" /></span>
          <span><b>{lead.name.split(" ")[0]}-tailored draft</b> · cites Series C, mentions SLA</span>
          <span className="grow" />
          <span className="conf">90% confident</span>
        </div>
        <textarea value={draft} onChange={(e) => setDraft(e.target.value)} />
        <div className="foot">
          <button className={`tone ${draftKind === "direct" ? "on" : ""}`} onClick={() => setDraftKind("direct")}>Direct</button>
          <button className={`tone ${draftKind === "warm" ? "on" : ""}`} onClick={() => setDraftKind("warm")}>Warm</button>
          <button className={`tone ${draftKind === "curious" ? "on" : ""}`} onClick={() => setDraftKind("curious")}>Curious</button>
          <span className="grow" />
          <button className="btn sm">Save draft</button>
          <button className="btn sm primary"><I.Reply width="12" height="12" /> Send</button>
        </div>
      </div>
    </>
  );
}

function Activity({ lead }) {
  const iconFor = (k) => ({
    cal: <I.Cal width="11" height="11" />,
    mail: <I.Mail width="11" height="11" />,
    ai: <I.Spark width="11" height="11" />,
    doc: <I.Doc width="11" height="11" />,
    form: <I.Check width="11" height="11" />,
    event: <I.Cal width="11" height="11" />,
  })[k] || <I.Clock width="11" height="11" />;
  return (
    <div className="tl">
      {lead.timeline.map((row, i) => (
        <div key={i} className="tl-row">
          <span className="w">{row.w}</span>
          <span className="d">{iconFor(row.k)}</span>
          <span className="t">{row.text || row.t}</span>
        </div>
      ))}
    </div>
  );
}

function Notes({ lead }) {
  const [val, setVal] = useS("");
  return (
    <>
      <div className="note">
        <div className="who"><span style={{ color: "#b48109", fontWeight: 600 }}>Sam Kovacs · 3d ago</span></div>
        Met {lead.name.split(" ")[0]} briefly at the SaaStr afterparty. Mentioned they're consolidating
        vendors after the round. Bring the consolidation deck to the demo.
      </div>
      <textarea
        className="field"
        placeholder="Add a note…"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        style={{ minHeight: 90 }}
      />
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
        <button className="btn sm primary" disabled={!val.trim()}>Save note</button>
      </div>
    </>
  );
}

// ─── Modals ──────────────────────────────────────────────────────
function ModalShell({ modal, close }) {
  if (!modal) return null;
  return (
    <div className="modal-scrim" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className={`modal ${modal.size === "lg" ? "lg" : ""}`}>
        <div className="modal-h">
          <span className="t">{modal.title}</span>
          <button className="iconbtn" onClick={close}><I.X width="14" height="14" /></button>
        </div>
        <div className="modal-b">{modal.body(close)}</div>
      </div>
    </div>
  );
}

function AskAi({ close, toast, onSeg }) {
  const [q, setQ] = useS("Which leads should I prioritise this morning?");
  const [stage, setStage] = useS("idle");
  const [ans, setAns] = useS(null);
  const ref = useR(null);
  useE(() => { ref.current?.focus(); }, []);
  const suggest = [
    "Which leads should I prioritise this morning?",
    "Who's stalled and how do I unblock them?",
    "Draft replies to all unread inbound.",
    "Summarise what changed since yesterday.",
  ];
  const ask = () => {
    setStage("thinking");
    setTimeout(() => {
      setAns({
        plan: [
          { name: "Priya Raghavan", why: "Demo booked 12m ago + $48M Series C — call window closes in <60 min." },
          { name: "Arjun Kapoor",   why: "Mid-vendor evaluation, replies in minutes. Speed wins." },
          { name: "Vikram Iyer",    why: "Referral from Tessera, founder-led, short cycle." },
          { name: "Ananya Nair",    why: "Send clean MSA — counsel's back Tuesday." },
        ],
        defer: [{ name: "Meera Bhatia", why: "Pause until CRO hire announced at Brightline." }],
      });
      setStage("done");
    }, 700);
  };
  return (
    <>
      <div style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--accent)", fontSize: 12, marginBottom: 10 }}>
        <I.Spark width="13" height="13" /> Across <b>{window.LEADS.length}</b> leads · last 30 days
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <input ref={ref} className="field" style={{ flex: 1 }} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") ask(); }} />
        <button className="btn primary" onClick={ask} disabled={stage === "thinking"}>
          {stage === "thinking" ? "Thinking…" : "Ask"}
        </button>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
        {suggest.map(s => <button key={s} className="chip" onClick={() => setQ(s)}>{s}</button>)}
      </div>
      {stage === "thinking" && (
        <div style={{ padding: 24, textAlign: "center", color: "var(--muted)", fontSize: 12, marginTop: 16 }}>
          <I.Spark width="14" height="14" /> thinking through {window.LEADS.length} leads…
        </div>
      )}
      {stage === "done" && ans && (
        <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--line)" }}>
          <div style={{ fontSize: 13, color: "var(--ink)", marginBottom: 12, lineHeight: 1.55 }}>
            Four leads are time-sensitive this morning; one is best deferred.
          </div>
          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.06, color: "var(--muted)", marginBottom: 8, fontWeight: 500 }}>
            Call / reply first
          </div>
          {ans.plan.map((p, i) => (
            <div key={i} style={{ display: "flex", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--line-2)" }}>
              <div style={{ width: 20, height: 20, borderRadius: "50%", background: "var(--ink)", color: "white", display: "grid", placeItems: "center", fontSize: 11, fontWeight: 600, flex: "0 0 20px" }}>{i + 1}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: "var(--muted)" }}>{p.why}</div>
              </div>
            </div>
          ))}
          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.06, color: "var(--muted)", margin: "14px 0 8px", fontWeight: 500 }}>Defer</div>
          {ans.defer.map((p, i) => (
            <div key={i} style={{ display: "flex", gap: 10, padding: "8px 0", color: "var(--muted)" }}>
              <I.Snooze width="14" height="14" />
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--ink-2)" }}>{p.name}</div>
                <div style={{ fontSize: 12 }}>{p.why}</div>
              </div>
            </div>
          ))}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, paddingTop: 14, marginTop: 14, borderTop: "1px solid var(--line)" }}>
            <button className="btn" onClick={close}>Close</button>
            <button className="btn primary" onClick={() => { onSeg("hot"); toast("Filtered to AI priorities"); close(); }}>
              Show these leads <I.Right width="11" height="11" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}

// ─── App root ────────────────────────────────────────────────────
function App() {
  const { leads, updateLead, markRead, appendActivity, toast, toasts, dismiss, modal, setModal } = useAppState();
  const [activeSeg, setActiveSeg] = useS("today");
  const [search, setSearch] = useS("");
  const [filters, setFilters] = useS([]);
  const [sort, setSort] = useS({ id: "score", dir: "desc" });
  const [density, setDensity] = useS("comfy");
  const [selectedId, setSelectedId] = useS(null);
  const [rowMore, setRowMore] = useS(null);
  const [assign, setAssign] = useS(null);

  const counts = useM(() => ({
    all:     leads.length,
    today:   leads.filter(l => inSeg(l, "today")).length,
    hot:     leads.filter(l => inSeg(l, "hot")).length,
    stalled: leads.filter(l => inSeg(l, "stalled")).length,
    mine:    leads.filter(l => inSeg(l, "mine")).length,
  }), [leads]);

  const filtered = useM(() => {
    let list = leads.filter(l => inSeg(l, activeSeg));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(l =>
        l.name.toLowerCase().includes(q) ||
        l.company.toLowerCase().includes(q) ||
        l.title.toLowerCase().includes(q) ||
        l.signals.some(s => s.label.toLowerCase().includes(q))
      );
    }
    for (const f of filters) {
      if (f.field === "Stage")  list = list.filter(l => l.stage === f.value);
      if (f.field === "Score")  list = list.filter(l => l.score >= Number(f.value));
      if (f.field === "Owner")  list = list.filter(l => l.owner === f.value);
      if (f.field === "Source") list = list.filter(l => l.source === f.value);
      if (f.field === "Temp")   list = list.filter(l => l.temp === f.value);
    }
    const dir = sort.dir === "desc" ? -1 : 1;
    list = [...list].sort((a, b) => {
      let av = a[sort.id], bv = b[sort.id];
      if (typeof av === "string") return av.localeCompare(bv) * dir;
      return (av - bv) * dir;
    });
    return list;
  }, [leads, activeSeg, search, filters, sort]);

  const selected = leads.find(l => l.id === selectedId);

  const openLead = (lead) => {
    setSelectedId(lead.id);
    if (lead.unread > 0) markRead(lead.id);
  };
  const prevLead = () => {
    if (!selected) return;
    const i = filtered.findIndex(l => l.id === selected.id);
    if (i > 0) openLead(filtered[i - 1]);
  };
  const nextLead = () => {
    if (!selected) return;
    const i = filtered.findIndex(l => l.id === selected.id);
    if (i < filtered.length - 1) openLead(filtered[i + 1]);
  };

  const onAction = (action, lead, anchor) => {
    switch (action) {
      case "reply":
        openLead(lead);
        break;
      case "qualify": {
        const ns = nextStage(lead.stage);
        updateLead(lead.id, { stage: ns });
        appendActivity(lead.id, { k: "form", text: `Stage → ${ns}` });
        toast(`${lead.name.split(" ")[0]} → ${ns}`, { tone: "success" });
        break;
      }
      case "schedule":
        appendActivity(lead.id, { k: "cal", text: "Schedule modal opened" });
        toast(`Schedule with ${lead.name.split(" ")[0]} (mock)`);
        break;
      case "snooze":
        toast(`Snoozed ${lead.name.split(" ")[0]} 3d`);
        break;
      case "assign":
        setAssign({ el: anchor, id: lead.id });
        break;
      case "row-more":
        setRowMore({ el: anchor, id: lead.id });
        break;
    }
  };
  const onAskAi = () => setModal({
    title: "Ask Lume",
    size: "lg",
    body: (close) => <AskAi close={close} toast={toast} onSeg={setActiveSeg} />,
  });
  const onNew = () => toast("New lead flow (demo)");

  useE(() => {
    const onKey = (e) => {
      if (e.key === "Escape") setSelectedId(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <div className="app">
        <Sidebar counts={counts} activeSeg={activeSeg} setActiveSeg={setActiveSeg} />
        <div className="main">
          <TopBar search={search} setSearch={setSearch} />
          <PageHeader counts={counts} onAskAi={onAskAi} onNew={onNew} onSeg={setActiveSeg} />
          <Toolbar
            activeSeg={activeSeg} setActiveSeg={setActiveSeg}
            counts={counts}
            density={density} setDensity={setDensity}
            sort={sort} setSort={setSort}
            filters={filters} setFilters={setFilters}
          />
          <LeadTable
            leads={filtered}
            selectedId={selectedId}
            onSelect={openLead}
            density={density}
            sort={sort} setSort={setSort}
            onAction={onAction}
          />
        </div>
      </div>

      <Drawer
        lead={selected}
        onClose={() => setSelectedId(null)}
        onPrev={prevLead}
        onNext={nextLead}
        onAction={onAction}
      />

      <ModalShell modal={modal} close={() => setModal(null)} />

      {rowMore && (() => {
        const lead = leads.find(l => l.id === rowMore.id);
        return (
          <Popover anchor={rowMore.el} onClose={() => setRowMore(null)} align="right">
            <div className="mi" onClick={() => { onAction("qualify", lead); setRowMore(null); }}><span className="ic"><I.Check width="13" height="13" /></span>Qualify</div>
            <div className="mi" onClick={() => { onAction("schedule", lead); setRowMore(null); }}><span className="ic"><I.Cal width="13" height="13" /></span>Schedule</div>
            <div className="mi" onClick={() => { onAction("reply", lead); setRowMore(null); }}><span className="ic"><I.Reply width="13" height="13" /></span>Reply</div>
            <div className="mi" onClick={(e) => { setAssign({ el: e.currentTarget, id: lead.id }); setRowMore(null); }}><span className="ic"><I.Assign width="13" height="13" /></span>Assign</div>
            <div className="mi" onClick={() => { onAction("snooze", lead); setRowMore(null); }}><span className="ic"><I.Snooze width="13" height="13" /></span>Snooze</div>
            <div className="sep" />
            <div className="mi danger" onClick={() => { toast(`Disqualified ${lead.name.split(" ")[0]}`); setRowMore(null); }}><span className="ic"><I.X width="13" height="13" /></span>Disqualify</div>
          </Popover>
        );
      })()}

      {assign && (
        <Popover anchor={assign.el} onClose={() => setAssign(null)} align="left">
          <div className="h">Assign owner</div>
          {Object.keys(window.OWNER_COLORS).map(o => {
            const oc = window.OWNER_COLORS[o];
            return (
              <div key={o} className="mi" onClick={() => {
                updateLead(assign.id, { owner: o });
                toast(`Assigned to ${oc.name}`);
                setAssign(null);
              }}>
                <span className={`av sm ${ownerClass(o)}`} style={{ marginRight: 2 }}>{oc.init}</span>
                {oc.name}
              </div>
            );
          })}
        </Popover>
      )}

      <div className="toasts">
        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.tone === "success" ? "success" : ""}`}>
            <span className="m">{t.message}</span>
            <button className="iconbtn" onClick={() => dismiss(t.id)} style={{ color: "white", opacity: 0.6 }}><I.X width="11" height="11" /></button>
          </div>
        ))}
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
