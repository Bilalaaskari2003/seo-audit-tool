import { useState, useEffect, useCallback } from "react";
import {
  Search, CheckCircle2, AlertTriangle, XCircle, Info,
  Download, Globe, Shield, Zap, Link2, BarChart2, Lock,
  Share2, ChevronDown, ChevronRight, ArrowLeft, FileText,
  Image as Img, Loader2, TrendingUp, Star, RefreshCw
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, RadarChart, PolarGrid,
  PolarAngleAxis, Radar
} from "recharts";

/* ─── Design tokens ─────────────────────────────────────────────────────────── */
const T = {
  bg:          "#06101e",
  surface:     "#0b1726",
  surface2:    "#101f33",
  border:      "#192d48",
  borderBright:"#234060",
  accent:      "#22d3ee",
  accentDim:   "rgba(34,211,238,.1)",
  green:       "#4ade80",
  greenDim:    "rgba(74,222,128,.1)",
  amber:       "#fbbf24",
  amberDim:    "rgba(251,191,36,.1)",
  red:         "#f87171",
  redDim:      "rgba(248,113,113,.1)",
  violet:      "#a78bfa",
  violetDim:   "rgba(167,139,250,.1)",
  text:        "#7a9abf",
  textBright:  "#dbeafe",
  textDim:     "#1e3a55",
};

const SEV = {
  critical: { color: T.red,    bg: T.redDim,    Icon: XCircle,       label: "Critical" },
  warning:  { color: T.amber,  bg: T.amberDim,  Icon: AlertTriangle,  label: "Warning"  },
  info:     { color: T.violet, bg: T.violetDim, Icon: Info,           label: "Info"     },
  pass:     { color: T.green,  bg: T.greenDim,  Icon: CheckCircle2,   label: "Pass"     },
};

const CATS = [
  { name: "Technical",   Icon: Zap      },
  { name: "Meta Tags",   Icon: Globe    },
  { name: "Performance", Icon: BarChart2 },
  { name: "Content",     Icon: FileText },
  { name: "Images",      Icon: Img      },
  { name: "Headings",    Icon: FileText },
  { name: "Links",       Icon: Link2    },
  { name: "Security",    Icon: Lock     },
  { name: "Social",      Icon: Share2   },
];

const scoreColor = (s) => s >= 80 ? T.green : s >= 55 ? T.amber : T.red;
const scoreLabel = (s) => s >= 80 ? "Excellent" : s >= 65 ? "Good" : s >= 45 ? "Needs Work" : "Poor";

/* ─── API config ────────────────────────────────────────────────────────────── */
// Uses the FREE FastAPI backend — real HTTP crawl + BeautifulSoup SEO analysis.
// No Anthropic API key needed.
const API_BASE = (typeof process !== "undefined" && process.env?.REACT_APP_API_URL) || "http://localhost:8000";

async function fetchAudit(url, onProgress) {
  // 1. Start async audit — backend returns report_id immediately
  const startRes = await fetch(`${API_BASE}/api/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, pages_to_check: 1 }),
  });
  if (!startRes.ok) {
    let detail = `Backend error ${startRes.status}`;
    try { const d = await startRes.json(); detail = d.detail || detail; } catch {}
    throw new Error(detail);
  }
  const { report_id } = await startRes.json();

  // 2. Poll every 1.2s until audit completes
  while (true) {
    await new Promise((r) => setTimeout(r, 1200));
    const pollRes = await fetch(`${API_BASE}/api/audit/${report_id}`);
    if (!pollRes.ok) throw new Error(`Polling error ${pollRes.status}`);
    const data = await pollRes.json();

    if (data.status === "in_progress" && onProgress) {
      onProgress(data.progress?.percentage ?? 0, data.progress?.message ?? "");
    }
    if (data.status === "complete") {
      const r = data.report;
      return {
        overallScore: r.overall_score,
        pageTitle:    new URL(url).hostname,
        categories:   r.categories,
        summary:      r.summary,
      };
    }
    if (data.status === "error") {
      throw new Error(data.progress?.message || "Audit failed on server.");
    }
  }
}


/* ─── Score ring ────────────────────────────────────────────────────────────── */
function ScoreRing({ score, size = 148 }) {
  const r = (size - 18) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = scoreColor(score);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={T.border} strokeWidth="9" />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth="9"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: "stroke-dashoffset 1.4s cubic-bezier(.34,1.56,.64,1)" }}
      />
    </svg>
  );
}

/* ─── Severity badge ────────────────────────────────────────────────────────── */
function Badge({ severity, compact }) {
  const s = SEV[severity] || SEV.info;
  const { Icon } = s;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 3,
      background: s.bg, color: s.color, borderRadius: 999,
      padding: compact ? "2px 7px" : "3px 10px",
      fontSize: compact ? 10 : 11, fontWeight: 700,
      textTransform: "uppercase", letterSpacing: ".06em", whiteSpace: "nowrap",
    }}>
      <Icon size={compact ? 9 : 11} />
      {!compact && s.label}
    </span>
  );
}

/* ─── Issue accordion row ───────────────────────────────────────────────────── */
function IssueRow({ issue, expanded, onToggle }) {
  const [hov, setHov] = useState(false);
  return (
    <div style={{ borderBottom: `1px solid ${T.border}` }}>
      <div
        onClick={onToggle}
        onMouseEnter={() => setHov(true)}
        onMouseLeave={() => setHov(false)}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "11px 18px", cursor: "pointer",
          background: hov ? T.surface2 : "transparent",
          transition: "background .15s",
        }}
      >
        <Badge severity={issue.severity} compact />
        <span style={{ flex: 1, color: T.textBright, fontSize: 13.5, fontWeight: 500 }}>
          {issue.title}
        </span>
        {issue.autoFixable && (
          <span style={{
            fontSize: 10, padding: "2px 8px", borderRadius: 4, fontWeight: 700,
            background: T.accentDim, color: T.accent, letterSpacing: ".05em",
          }}>
            AUTO-FIX
          </span>
        )}
        <span style={{ fontSize: 10, color: T.textDim, textTransform: "uppercase", letterSpacing: ".04em", minWidth: 44, textAlign: "right" }}>
          {issue.impact}
        </span>
        <ChevronRight size={13} color={T.textDim} style={{
          flexShrink: 0,
          transform: expanded ? "rotate(90deg)" : "none",
          transition: "transform .2s",
        }} />
      </div>
      {expanded && (
        <div style={{ padding: "4px 18px 16px 18px", background: T.surface2 }}>
          <p style={{ margin: "0 0 10px", fontSize: 13, color: T.text, lineHeight: 1.65 }}>
            {issue.description}
          </p>
          <div style={{
            padding: "10px 14px", borderRadius: 8,
            border: `1px solid ${T.accent}33`, background: T.accentDim, marginBottom: 8,
          }}>
            <span style={{ fontSize: 11, color: T.accent, fontWeight: 700 }}>RECOMMENDATION → </span>
            <span style={{ fontSize: 13, color: T.textBright }}>{issue.recommendation}</span>
          </div>
          {(issue.currentValue || issue.expectedValue) && (
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {issue.currentValue && (
                <span style={{ fontSize: 12, color: T.text }}>
                  <span style={{ color: T.textDim }}>Current: </span>
                  <code style={{ color: T.amber, background: T.amberDim, padding: "1px 6px", borderRadius: 3, fontSize: 11 }}>
                    {issue.currentValue}
                  </code>
                </span>
              )}
              {issue.expectedValue && (
                <span style={{ fontSize: 12, color: T.text }}>
                  <span style={{ color: T.textDim }}>Expected: </span>
                  <code style={{ color: T.green, background: T.greenDim, padding: "1px 6px", borderRadius: 3, fontSize: 11 }}>
                    {issue.expectedValue}
                  </code>
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Loading screen ────────────────────────────────────────────────────────── */
const TICKS = [
  "Resolving domain…", "Fetching page HTML…", "Parsing meta tags…",
  "Checking Open Graph tags…", "Scanning heading structure…", "Auditing images…",
  "Analyzing link graph…", "Checking content depth…", "Verifying HTTPS & headers…",
  "Checking Schema.org markup…", "Verifying robots.txt & sitemap…",
  "Analyzing performance signals…", "Calculating weighted scores…",
];

function LoadingScreen({ url, liveMsg }) {
  const [tick, setTick] = useState(0);
  const [pct, setPct] = useState(0);
  useEffect(() => {
    const id = setInterval(() => {
      setTick((t) => Math.min(t + 1, TICKS.length - 1));
      setPct((p) => Math.min(p + 100 / TICKS.length, 94));
    }, 750);
    return () => clearInterval(id);
  }, []);
  const visible = TICKS.slice(Math.max(0, tick - 4), tick + 1);
  // If backend sends a real progress message, show it as the active step
  const activeMsg = liveMsg || visible[visible.length - 1] || "";
  return (
    <div style={{ maxWidth: 520, margin: "0 auto", padding: "72px 24px", textAlign: "center" }}>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      <Loader2 size={56} color={T.accent} style={{ animation: "spin 1s linear infinite", marginBottom: 26 }} />
      <h2 style={{ color: T.textBright, fontSize: 20, fontWeight: 700, margin: "0 0 8px", letterSpacing: "-.02em" }}>
        Auditing {url.replace(/^https?:\/\//, "")}
      </h2>
      <p style={{ color: T.text, fontSize: 14, margin: "0 0 34px", lineHeight: 1.6 }}>
        Running 80+ real SEO checks across 9 categories…
      </p>
      <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 14, overflow: "hidden" }}>
        <div style={{ height: 3, background: T.border }}>
          <div style={{ height: "100%", background: T.accent, borderRadius: 2, width: `${pct}%`, transition: "width .75s ease" }} />
        </div>
        <div style={{ padding: "20px 22px" }}>
          {visible.slice(0, -1).map((t) => (
            <div key={t} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, opacity: 0.3 }}>
              <CheckCircle2 size={13} color={T.green} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: 13, color: T.text }}>{t}</span>
            </div>
          ))}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Loader2 size={13} color={T.accent} style={{ animation: "spin 1s linear infinite", flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: T.accent }}>{activeMsg}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Custom recharts tooltip ───────────────────────────────────────────────── */
function ChartTip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { name, score } = payload[0].payload;
  return (
    <div style={{ background: T.surface2, border: `1px solid ${T.borderBright}`, borderRadius: 8, padding: "8px 14px" }}>
      <div style={{ fontSize: 11, color: T.text, marginBottom: 2 }}>{name?.replace("\n", " ")}</div>
      <div style={{ fontSize: 22, fontWeight: 800, color: scoreColor(score) }}>{score}</div>
    </div>
  );
}

/* ─── Results dashboard ─────────────────────────────────────────────────────── */
function Results({ report, url, onReset }) {
  const [activeTab, setActiveTab] = useState("all");
  const [sevFilter, setSevFilter] = useState("all");
  const [expanded, setExpanded] = useState(null);
  const [chartMode, setChartMode] = useState("bar");

  const catKeys = CATS.map((c) => c.name).filter((n) => report.categories?.[n]);
  const cats = report.categories || {};

  const allIssues = catKeys.flatMap((cat) =>
    (cats[cat]?.issues || []).map((i) => ({ ...i, _cat: cat }))
  );

  const quickWins = allIssues.filter(
    (i) => i.autoFixable && (i.severity === "critical" || i.severity === "warning")
  );

  const baseIssues = activeTab === "all" ? allIssues : (cats[activeTab]?.issues || []).map((i) => ({ ...i, _cat: activeTab }));
  const filteredIssues = sevFilter === "all" ? baseIssues : baseIssues.filter((i) => i.severity === sevFilter);

  const summary = {
    critical: allIssues.filter((i) => i.severity === "critical").length,
    warning:  allIssues.filter((i) => i.severity === "warning").length,
    info:     allIssues.filter((i) => i.severity === "info").length,
    pass:     allIssues.filter((i) => i.severity === "pass").length,
  };

  const barData = catKeys.map((cat) => ({ name: cat.replace(" ", "\n"), score: cats[cat]?.score ?? 0 }));
  const radarData = catKeys.map((cat) => ({ cat: cat.length > 9 ? cat.slice(0, 9) + "…" : cat, score: cats[cat]?.score ?? 0 }));
  const score = report.overallScore ?? 0;

  const doExport = (fmt) => {
    let hostname = url;
    try { hostname = new URL(url).hostname; } catch {}
    if (fmt === "json") {
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
      a.download = `seo_${hostname}.json`; a.click();
    } else {
      const q = (v) => `"${String(v ?? "").replace(/"/g, "'")}"`;
      const hdr = ["Category","Severity","Impact","AutoFix","Title","Description","Recommendation","Current","Expected"];
      const rows = allIssues.map((i) => [i._cat,i.severity,i.impact,i.autoFixable,i.title,i.description,i.recommendation,i.currentValue,i.expectedValue].map(q));
      const blob = new Blob([[hdr, ...rows].map((r) => r.join(",")).join("\n")], { type: "text/csv" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
      a.download = `seo_${hostname}.csv`; a.click();
    }
  };

  const PillBtn = ({ label, active, onClick, color }) => (
    <button onClick={onClick} style={{
      padding: "4px 11px", borderRadius: 7,
      border: `1px solid ${active ? (color || T.borderBright) : T.border}`,
      background: active ? (color ? color + "22" : T.surface2) : "transparent",
      color: active ? (color || T.textBright) : T.text,
      fontSize: 12, cursor: "pointer", fontWeight: active ? 700 : 400,
      transition: "all .15s", whiteSpace: "nowrap",
    }}>
      {label}
    </button>
  );

  return (
    <div style={{ maxWidth: 1060, margin: "0 auto", paddingBottom: 64 }}>
      {/* ── Sticky top bar ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "13px 24px", borderBottom: `1px solid ${T.border}`,
        background: T.surface, position: "sticky", top: 0, zIndex: 10,
        flexWrap: "wrap", gap: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={onReset} style={{
            background: "none", border: `1px solid ${T.border}`, borderRadius: 8,
            padding: "5px 12px", color: T.text, cursor: "pointer",
            display: "flex", alignItems: "center", gap: 5, fontSize: 12,
          }}>
            <ArrowLeft size={12} /> New Audit
          </button>
          <Globe size={14} color={T.accent} />
          <span style={{ color: T.text, fontSize: 13, fontFamily: "monospace", wordBreak: "break-all" }}>
            {url.replace(/^https?:\/\//, "")}
          </span>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {[["JSON","json"],["CSV","csv"]].map(([lbl,fmt]) => (
            <button key={fmt} onClick={() => doExport(fmt)} style={{
              background: T.surface2, border: `1px solid ${T.border}`, borderRadius: 8,
              padding: "5px 12px", color: T.text, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 5, fontSize: 12,
            }}>
              <Download size={12} /> {lbl}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: "26px 24px" }}>
        {/* ── Overview row ── */}
        <div style={{ display: "grid", gridTemplateColumns: "192px 1fr", gap: 18, marginBottom: 22 }}>

          {/* Score card */}
          <div style={{
            background: T.surface, border: `1px solid ${T.border}`,
            borderRadius: 16, padding: "22px 14px",
            display: "flex", flexDirection: "column", alignItems: "center",
          }}>
            <div style={{ position: "relative" }}>
              <ScoreRing score={score} size={148} />
              <div style={{
                position: "absolute", top: "50%", left: "50%",
                transform: "translate(-50%,-50%)", textAlign: "center", pointerEvents: "none",
              }}>
                <div style={{ fontSize: 40, fontWeight: 900, color: scoreColor(score), lineHeight: 1 }}>{score}</div>
                <div style={{ fontSize: 10, color: T.text, marginTop: 4, letterSpacing: ".1em", textTransform: "uppercase" }}>Score</div>
              </div>
            </div>
            <div style={{ marginTop: 8, fontSize: 14, fontWeight: 700, color: scoreColor(score) }}>
              {scoreLabel(score)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7, width: "100%", marginTop: 16 }}>
              {[
                { label: "Critical", value: summary.critical, color: T.red    },
                { label: "Warnings", value: summary.warning,  color: T.amber  },
                { label: "Info",     value: summary.info,     color: T.violet },
                { label: "Passed",   value: summary.pass,     color: T.green  },
              ].map((s) => (
                <div key={s.label} style={{
                  textAlign: "center", padding: "8px 4px",
                  background: T.surface2, borderRadius: 8, border: `1px solid ${T.border}`,
                }}>
                  <div style={{ fontSize: 20, fontWeight: 800, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 10, color: T.text, marginTop: 2, textTransform: "uppercase", letterSpacing: ".05em" }}>
                    {s.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Chart card */}
          <div style={{
            background: T.surface, border: `1px solid ${T.border}`,
            borderRadius: 16, padding: "18px 16px",
          }}>
            <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
              <PillBtn label="Bar Chart" active={chartMode === "bar"} onClick={() => setChartMode("bar")} />
              <PillBtn label="Radar" active={chartMode === "radar"} onClick={() => setChartMode("radar")} />
            </div>
            {chartMode === "bar" ? (
              <ResponsiveContainer width="100%" height={195}>
                <BarChart data={barData} barSize={24} margin={{ left: -10, right: 6, bottom: 10 }}>
                  <XAxis dataKey="name" tick={{ fill: T.text, fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: T.text, fontSize: 10 }} axisLine={false} tickLine={false} width={26} />
                  <Tooltip content={<ChartTip />} cursor={{ fill: "rgba(255,255,255,.03)" }} />
                  <Bar dataKey="score" radius={[5, 5, 0, 0]}>
                    {barData.map((d, i) => <Cell key={i} fill={scoreColor(d.score)} fillOpacity={0.85} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <ResponsiveContainer width="100%" height={195}>
                <RadarChart data={radarData} margin={{ top: 6, right: 20, bottom: 6, left: 20 }}>
                  <PolarGrid stroke={T.border} />
                  <PolarAngleAxis dataKey="cat" tick={{ fill: T.text, fontSize: 10 }} />
                  <Radar dataKey="score" stroke={T.accent} fill={T.accent} fillOpacity={0.13} dot={{ fill: T.accent, r: 3 }} />
                </RadarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* ── Category cards ── */}
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(148px,1fr))",
          gap: 10, marginBottom: 22,
        }}>
          {catKeys.map((cat) => {
            const { Icon } = CATS.find((c) => c.name === cat) || { Icon: Globe };
            const s = cats[cat]?.score ?? 0;
            const issues = cats[cat]?.issues || [];
            const crit = issues.filter((i) => i.severity === "critical").length;
            const warn = issues.filter((i) => i.severity === "warning").length;
            const isActive = activeTab === cat;
            return (
              <button key={cat} onClick={() => { setActiveTab(isActive ? "all" : cat); setSevFilter("all"); }} style={{
                background: isActive ? T.surface2 : T.surface,
                border: `1px solid ${isActive ? T.accent + "88" : T.border}`,
                borderRadius: 12, padding: "13px 13px", cursor: "pointer",
                textAlign: "left", transition: "all .18s",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 7 }}>
                  <Icon size={16} color={scoreColor(s)} />
                  <span style={{ fontSize: 20, fontWeight: 800, color: scoreColor(s), lineHeight: 1 }}>{s}</span>
                </div>
                <div style={{ fontSize: 12, color: T.textBright, fontWeight: 600, marginBottom: 4 }}>{cat}</div>
                <div style={{ fontSize: 11 }}>
                  {crit > 0 && <span style={{ color: T.red }}>● {crit} crit  </span>}
                  {warn > 0 && <span style={{ color: T.amber }}>● {warn} warn</span>}
                  {crit === 0 && warn === 0 && <span style={{ color: T.green }}>● clean</span>}
                </div>
              </button>
            );
          })}
        </div>

        {/* ── Quick wins callout ── */}
        {quickWins.length > 0 && (
          <div style={{
            background: T.accentDim, border: `1px solid ${T.accent}44`,
            borderRadius: 12, padding: "14px 18px", marginBottom: 22,
            display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
          }}>
            <Star size={18} color={T.accent} style={{ flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 200 }}>
              <span style={{ color: T.accent, fontWeight: 700, fontSize: 14 }}>
                {quickWins.length} Quick Win{quickWins.length > 1 ? "s" : ""} Available
              </span>
              <span style={{ color: T.text, fontSize: 13, marginLeft: 8 }}>
                — these issues can be automatically fixed with admin access.
              </span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {quickWins.slice(0, 4).map((w, i) => (
                <span key={i} style={{
                  fontSize: 11, padding: "3px 10px", borderRadius: 6,
                  background: T.surface2, color: T.text, border: `1px solid ${T.border}`,
                  maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>{w.title}</span>
              ))}
              {quickWins.length > 4 && (
                <span style={{ fontSize: 11, color: T.accent }}>+{quickWins.length - 4} more</span>
              )}
            </div>
          </div>
        )}

        {/* ── Issues panel ── */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, overflow: "hidden" }}>
          {/* Toolbar */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "13px 18px", borderBottom: `1px solid ${T.border}`,
            flexWrap: "wrap", gap: 10,
          }}>
            {/* Tab row */}
            <div style={{ display: "flex", gap: 5, flexWrap: "wrap", alignItems: "center" }}>
              <PillBtn label={`All (${allIssues.length})`} active={activeTab === "all"} onClick={() => { setActiveTab("all"); setSevFilter("all"); }} />
              {catKeys.map((cat) => (
                <PillBtn key={cat} label={cat} active={activeTab === cat} onClick={() => { setActiveTab(cat); setSevFilter("all"); }} />
              ))}
            </div>
            {/* Severity filter */}
            <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
              {["all","critical","warning","info","pass"].map((f) => {
                const base = activeTab === "all" ? allIssues : (cats[activeTab]?.issues || []);
                const cnt = f === "all" ? base.length : base.filter((i) => i.severity === f).length;
                const sc = SEV[f];
                return (
                  <PillBtn
                    key={f} label={`${f} (${cnt})`}
                    active={sevFilter === f}
                    onClick={() => setSevFilter(f)}
                    color={sc?.color}
                  />
                );
              })}
            </div>
          </div>

          {/* Count bar */}
          <div style={{ padding: "8px 18px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 12, color: T.text }}>
              Showing <span style={{ color: T.textBright, fontWeight: 600 }}>{filteredIssues.length}</span> issue{filteredIssues.length !== 1 ? "s" : ""}
              {activeTab !== "all" && <span> in <strong style={{ color: T.accent }}>{activeTab}</strong></span>}
              {sevFilter !== "all" && <span> · <Badge severity={sevFilter} compact /></span>}
            </span>
            {expanded !== null && (
              <button onClick={() => setExpanded(null)} style={{ background: "none", border: "none", color: T.text, fontSize: 12, cursor: "pointer" }}>
                Collapse all
              </button>
            )}
          </div>

          {/* Rows */}
          {filteredIssues.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: T.text }}>
              No issues match the selected filters.
            </div>
          ) : (
            filteredIssues.map((issue, idx) => {
              const key = issue.id ? `${issue._cat}_${issue.id}` : `${issue._cat}_${idx}`;
              return (
                <IssueRow
                  key={key}
                  issue={issue}
                  expanded={expanded === key}
                  onToggle={() => setExpanded(expanded === key ? null : key)}
                />
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Input screen ──────────────────────────────────────────────────────────── */
function InputScreen({ onAudit }) {
  const [url, setUrl] = useState("");
  const [showCreds, setShowCreds] = useState(false);
  const [creds, setCreds] = useState({ apiUrl: "", username: "", password: "" });
  const [focused, setFocused] = useState(false);

  const submit = () => {
    let u = url.trim();
    if (!u) return;
    if (!u.startsWith("http")) u = "https://" + u;
    onAudit(u, showCreds && creds.username ? creds : null);
  };

  const EXAMPLES = ["github.com", "shopify.com", "stripe.com", "medium.com"];

  return (
    <div style={{ maxWidth: 570, margin: "0 auto", padding: "64px 24px 40px" }}>
      {/* Hero */}
      <div style={{ textAlign: "center", marginBottom: 44 }}>
        <div style={{
          width: 74, height: 74, borderRadius: 22, margin: "0 auto 20px",
          background: T.accentDim, border: `1px solid ${T.accent}44`,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <TrendingUp size={36} color={T.accent} />
        </div>
        <h1 style={{ fontSize: 30, fontWeight: 800, color: T.textBright, margin: "0 0 10px", letterSpacing: "-.025em" }}>
          SEO Audit Tool
        </h1>
        <p style={{ color: T.text, fontSize: 14.5, margin: 0, lineHeight: 1.65 }}>
          AI-powered analysis — 80+ checks across 9 categories<br />
          with actionable recommendations and auto-fix support.
        </p>
      </div>

      {/* URL input */}
      <div style={{
        display: "flex", alignItems: "center",
        background: T.surface, borderRadius: 13,
        border: `1.5px solid ${focused ? T.accent : T.border}`,
        overflow: "hidden", marginBottom: 12, transition: "border-color .2s",
      }}>
        <Globe size={16} color={T.textDim} style={{ margin: "0 10px 0 16px", flexShrink: 0 }} />
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="https://yourwebsite.com"
          style={{
            flex: 1, background: "none", border: "none", outline: "none",
            color: T.textBright, fontSize: 15, padding: "16px 0",
            fontFamily: "monospace",
          }}
        />
        <button onClick={submit} style={{
          background: T.accent, border: "none", cursor: "pointer",
          padding: "10px 20px", margin: 6, borderRadius: 9,
          color: "#050e1c", fontWeight: 700, fontSize: 14,
          display: "flex", alignItems: "center", gap: 7,
          transition: "opacity .18s",
        }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = ".82")}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
        >
          <Search size={15} /> Audit
        </button>
      </div>

      {/* Example URLs */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, color: T.textDim }}>Try:</span>
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => setUrl("https://" + ex)} style={{
            background: "none", border: `1px solid ${T.border}`, borderRadius: 6,
            padding: "3px 10px", color: T.text, cursor: "pointer", fontSize: 12,
            transition: "all .15s",
          }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = T.accent; e.currentTarget.style.color = T.accent; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.text; }}
          >
            {ex}
          </button>
        ))}
      </div>

      {/* Optional admin credentials */}
      <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, overflow: "hidden" }}>
        <button onClick={() => setShowCreds(!showCreds)} style={{
          width: "100%", padding: "13px 18px", background: "none", border: "none",
          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
          color: T.text, fontSize: 13.5,
        }}>
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Lock size={15} color={T.textDim} />
            Admin access <span style={{ fontSize: 11, color: T.textDim }}>(optional — enables auto-fix)</span>
          </span>
          <ChevronDown size={15} style={{ transform: showCreds ? "rotate(180deg)" : "none", transition: "transform .2s" }} />
        </button>
        {showCreds && (
          <div style={{ padding: "0 18px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
            {[
              { key: "apiUrl",    label: "WP REST API URL",     placeholder: "https://example.com/wp-json" },
              { key: "username",  label: "Username",            placeholder: "admin" },
              { key: "password",  label: "Application Password", placeholder: "xxxx xxxx xxxx xxxx" },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label style={{ fontSize: 11, color: T.text, display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: ".05em" }}>
                  {label}
                </label>
                <input
                  type={key === "password" ? "password" : "text"}
                  value={creds[key]}
                  onChange={(e) => setCreds((c) => ({ ...c, [key]: e.target.value }))}
                  placeholder={placeholder}
                  style={{
                    width: "100%", background: T.surface2, border: `1px solid ${T.border}`,
                    borderRadius: 8, padding: "9px 13px", color: T.textBright, fontSize: 13,
                    outline: "none", boxSizing: "border-box",
                  }}
                />
              </div>
            ))}
            <p style={{ margin: 0, fontSize: 11, color: T.textDim, lineHeight: 1.5 }}>
              Credentials are used only for auto-fix via WP REST API and are never stored or transmitted elsewhere.
            </p>
          </div>
        )}
      </div>

      {/* Feature pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginTop: 22, justifyContent: "center" }}>
        {["80+ checks", "9 categories", "AI-powered", "Auto-fix ready", "JSON + CSV export", "Score 0–100"].map((f) => (
          <span key={f} style={{
            fontSize: 11.5, padding: "4px 12px", borderRadius: 999,
            background: T.surface, border: `1px solid ${T.border}`, color: T.text,
          }}>
            {f}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ─── Error screen ──────────────────────────────────────────────────────────── */
function ErrorScreen({ message, onRetry }) {
  return (
    <div style={{ textAlign: "center", padding: "80px 24px" }}>
      <XCircle size={52} color={T.red} style={{ marginBottom: 18 }} />
      <h2 style={{ color: T.textBright, margin: "0 0 10px", fontSize: 20, fontWeight: 700 }}>Audit Failed</h2>
      <p style={{ color: T.text, marginBottom: 28, fontSize: 14, maxWidth: 400, margin: "0 auto 28px", lineHeight: 1.6 }}>
        {message}
      </p>
      <button onClick={onRetry} style={{
        background: T.accent, border: "none", borderRadius: 9, padding: "10px 24px",
        color: "#050e1c", fontWeight: 700, cursor: "pointer",
        display: "inline-flex", alignItems: "center", gap: 8, fontSize: 14,
      }}>
        <RefreshCw size={15} /> Try Again
      </button>
    </div>
  );
}

/* ─── App root ──────────────────────────────────────────────────────────────── */
export default function SEOAuditTool() {
  const [phase, setPhase] = useState("input");
  const [url, setUrl] = useState("");
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap";
    document.head.appendChild(link);
  }, []);

  const [liveMsg, setLiveMsg] = useState("");

  const runAudit = useCallback(async (targetUrl) => {
    setUrl(targetUrl);
    setPhase("loading");
    setLiveMsg("");
    setError("");
    try {
      const data = await fetchAudit(targetUrl, (pct, msg) => setLiveMsg(msg));
      setReport(data);
      setPhase("results");
    } catch (err) {
      setError(err.message || "Audit failed. Check the URL and try again.");
      setPhase("error");
    }
  }, []);

  const reset = useCallback(() => {
    setPhase("input");
    setReport(null);
    setError("");
    setUrl("");
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: T.bg, fontFamily: '"DM Sans", system-ui, sans-serif', color: T.textBright }}>
      <style>{`*{box-sizing:border-box;} input::placeholder{color:${T.textDim};} button{font-family:inherit;} ::-webkit-scrollbar{width:6px;background:${T.surface};} ::-webkit-scrollbar-thumb{background:${T.border};border-radius:3px;}`}</style>
      {phase === "input"   && <InputScreen onAudit={runAudit} />}
      {phase === "loading" && <LoadingScreen url={url} liveMsg={liveMsg} />}
      {phase === "results" && report && <Results report={report} url={url} onReset={reset} />}
      {phase === "error"   && <ErrorScreen message={error} onRetry={reset} />}
    </div>
  );
}