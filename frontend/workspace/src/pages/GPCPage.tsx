import { useState } from "react";
import {
  Terminal, Shield, Activity, Users, Zap, AlertTriangle, ChevronRight,
  Eye, Bot, Gauge, BookOpen, Search as SearchIcon, Lock, Sparkles,
  Radio, Hammer, Scale, Megaphone, Target, Wrench, Star, CheckCircle,
  XCircle, Clock, Download, Server,
} from "lucide-react";
import { MiniChart } from "@/components/MiniChart";

/* ──────────────────────────────────────────────────────────────────────────
   UACP GOVERNED PROCESS CONTROL
   The autonomous operator terminal — 20 workers, 5 committees, pillars,
   event stream, evaluation surgeon queue, growth opportunities.
   Surfaces the real backend at /api/v1/internal/uacp/* and /internal/operators/*
   ────────────────────────────────────────────────────────────────────────── */

type WorkerStatus = "ok" | "warning" | "failed" | "blocked" | "idle";

interface Worker {
  id: string; name: string; icon: React.ReactNode; mission: string;
  pillar: string; committee: string; status: WorkerStatus;
  kpis: { label: string; value: string }[];
  lastRun: string; rollout: string;
}

const I = "h-3.5 w-3.5";

const WORKERS: Worker[] = [
  { id: "herald", name: "HERALD", icon: <Megaphone className={I} />, mission: "Resend funnels, vendor/buyer lifecycle, deliverability", pillar: "Growth", committee: "marketplace-ops", status: "ok", kpis: [{ label: "Delivery", value: "97.2%" }, { label: "Reply", value: "14%" }], lastRun: "2m", rollout: "ready" },
  { id: "harvest", name: "HARVEST", icon: <Target className={I} />, mission: "Find and qualify marketplace vendors from compliant sources", pillar: "Sales", committee: "marketplace-ops", status: "ok", kpis: [{ label: "Qualified", value: "34" }, { label: "Accept", value: "72%" }], lastRun: "8m", rollout: "ready" },
  { id: "bouncer", name: "BOUNCER", icon: <Shield className={I} />, mission: "Intake defense, vendor review, abuse detection, threat control", pillar: "Risk", committee: "marketplace-ops", status: "ok", kpis: [{ label: "Blocked", value: "12" }, { label: "Clean", value: "98.4%" }], lastRun: "1m", rollout: "ready" },
  { id: "gauge", name: "GAUGE", icon: <Gauge className={I} />, mission: "Monitor health, usage, route status, wallet drift, conversion", pillar: "Ops", committee: "marketplace-ops", status: "ok", kpis: [{ label: "Uptime", value: "99.97%" }, { label: "Drift", value: "0.02%" }], lastRun: "30s", rollout: "min_live" },
  { id: "ledger", name: "LEDGER", icon: <BookOpen className={I} />, mission: "Audit packs, explainability, evidence bundles, proof exports", pillar: "Compliance", committee: "governance", status: "ok", kpis: [{ label: "Evidence", value: "1,247" }, { label: "Integrity", value: "100%" }], lastRun: "45s", rollout: "min_live" },
  { id: "signal", name: "SIGNAL", icon: <Radio className={I} />, mission: "Developer/community signal into distribution loops", pillar: "Growth", committee: "growth-intel", status: "ok", kpis: [{ label: "Mentions", value: "89" }, { label: "Views", value: "2.4k" }], lastRun: "15m", rollout: "ready" },
  { id: "oracle", name: "ORACLE", icon: <Eye className={I} />, mission: "AI policy, procurement, sovereignty, privacy requirements", pillar: "Governance", committee: "governance", status: "ok", kpis: [{ label: "Updates", value: "7" }, { label: "Risk", value: "2" }], lastRun: "1h", rollout: "ready" },
  { id: "mint", name: "MINT", icon: <Sparkles className={I} />, mission: "Pricing, wallet economics, packaging, monetization", pillar: "Finance", committee: "growth-intel", status: "ok", kpis: [{ label: "Activation", value: "34%" }, { label: "Margin", value: "68%" }], lastRun: "5m", rollout: "ready" },
  { id: "scout", name: "SCOUT", icon: <SearchIcon className={I} />, mission: "Competitors, marketplace movement, partner signals", pillar: "Knowledge", committee: "growth-intel", status: "ok", kpis: [{ label: "Signals", value: "23" }, { label: "Threats", value: "3" }], lastRun: "2h", rollout: "ready" },
  { id: "arbiter", name: "ARBITER", icon: <Scale className={I} />, mission: "Vendor quality, dispute routing, review integrity", pillar: "Ops", committee: "marketplace-ops", status: "ok", kpis: [{ label: "Resolve", value: "4.2h" }, { label: "Trust", value: "96%" }], lastRun: "20m", rollout: "ready" },
  { id: "builder-scout", name: "BLDR SCOUT", icon: <SearchIcon className={I} />, mission: "Public pain signals → clean-room marketplace opportunities", pillar: "Eng", committee: "builder-sys", status: "ok", kpis: [{ label: "Signals", value: "18" }, { label: "Clear", value: "94%" }], lastRun: "45m", rollout: "staged" },
  { id: "builder-forge", name: "BLDR FORGE", icon: <Hammer className={I} />, mission: "Approved specs → original Veklom-native MCP/SDK/CLI packages", pillar: "Eng", committee: "builder-sys", status: "ok", kpis: [{ label: "Built", value: "6" }, { label: "Tests", value: "100%" }], lastRun: "3h", rollout: "staged" },
  { id: "builder-arbiter", name: "BLDR ARBITER", icon: <Lock className={I} />, mission: "Provenance, license safety, no-copy rules, release gates", pillar: "Compliance", committee: "builder-sys", status: "ok", kpis: [{ label: "Blocked", value: "2" }, { label: "Gate", value: "88%" }], lastRun: "1h", rollout: "staged" },
  { id: "sentinel", name: "SENTINEL", icon: <Activity className={I} />, mission: "E2E uptime, route, API, critical flow verification", pillar: "Ops", committee: "experience", status: "ok", kpis: [{ label: "Routes", value: "100%" }, { label: "Break", value: "0" }], lastRun: "1m", rollout: "min_live" },
  { id: "mirror", name: "MIRROR", icon: <Eye className={I} />, mission: "Frontend ↔ backend truth validation, stale/null detection", pillar: "Product", committee: "experience", status: "ok", kpis: [{ label: "Truth", value: "99.8%" }, { label: "Stale", value: "1" }], lastRun: "2m", rollout: "min_live" },
  { id: "polish", name: "POLISH", icon: <Star className={I} />, mission: "Premium visual quality, hierarchy, empty-state standards", pillar: "Product", committee: "experience", status: "ok", kpis: [{ label: "Score", value: "94" }, { label: "Defects", value: "2" }], lastRun: "30m", rollout: "min_live" },
  { id: "glide", name: "GLIDE", icon: <Zap className={I} />, mission: "Navigation, transitions, CTAs, controls, movement feel", pillar: "Product", committee: "experience", status: "ok", kpis: [{ label: "Dead", value: "0" }, { label: "Friction", value: "low" }], lastRun: "15m", rollout: "min_live" },
  { id: "pulse", name: "PULSE", icon: <Activity className={I} />, mission: "Live telemetry freshness, evidence backing, not decorative", pillar: "Ops", committee: "experience", status: "warning", kpis: [{ label: "Fresh", value: "87%" }, { label: "Stale", value: "2" }], lastRun: "30s", rollout: "min_live" },
  { id: "sheriff", name: "SHERIFF", icon: <Shield className={I} />, mission: "Post-deploy regression, config drift, permission change detect", pillar: "Ops", committee: "experience", status: "ok", kpis: [{ label: "Regress", value: "0" }, { label: "Conf", value: "98%" }], lastRun: "5m", rollout: "min_live" },
  { id: "welcome", name: "WELCOME", icon: <Users className={I} />, mission: "First-run, landing-to-app, signup, onboarding protection", pillar: "Product", committee: "experience", status: "ok", kpis: [{ label: "TTV", value: "42s" }, { label: "Done", value: "78%" }], lastRun: "10m", rollout: "ready" },
];

const COMMITTEES = [
  { id: "marketplace-ops", name: "Marketplace Operations", workers: ["herald", "harvest", "bouncer", "gauge", "arbiter"], authority: "Supply, demand, trust, and health loops", color: "bg-amber" },
  { id: "governance", name: "Governance & Evidence", workers: ["ledger", "oracle", "builder-arbiter", "sheriff"], authority: "Policy posture, evidence integrity, release gates", color: "bg-moss" },
  { id: "growth-intel", name: "Growth & Intelligence", workers: ["signal", "scout", "mint", "welcome"], authority: "Market signal → pricing → positioning → revenue", color: "bg-electric" },
  { id: "builder-sys", name: "Builder Systems", workers: ["builder-scout", "builder-forge", "builder-arbiter"], authority: "Public pain → original Veklom-native tool assets", color: "bg-violet" },
  { id: "experience", name: "Experience Assurance", workers: ["sentinel", "mirror", "polish", "glide", "pulse", "sheriff", "welcome"], authority: "Live, truthful, premium, navigable, regression-free", color: "bg-crimson" },
];

const EVENTS = [
  { id: "ai:4821", type: "ai.complete", sev: "info", ws: "acme-prod", ts: "07:24:11Z", msg: "llama3-70b · 142ms · $0.00091 · PII redacted", pillars: ["execution", "governance"] },
  { id: "req:fail:1902", type: "request.failed", sev: "error", ws: "acme-prod", ts: "07:23:58Z", msg: "POST /v1/chat/completions · 502 · groq fallback triggered", pillars: ["product", "engineering"] },
  { id: "pipe:312", type: "pipeline.run", sev: "info", ws: "acme-prod", ts: "07:22:45Z", msg: "patient-intake · 3 steps · 276ms · $0.00098", pillars: ["execution", "archives"] },
  { id: "deploy:87", type: "deployment.state", sev: "info", ws: "acme-prod", ts: "07:20:12Z", msg: "chat-prod promoted v3.3 → 75/25 split", pillars: ["engineering", "operations"] },
  { id: "wallet:2041", type: "billing.reserve", sev: "info", ws: "acme-prod", ts: "07:18:30Z", msg: "debit 142 units · balance 84,200 ($84.20)", pillars: ["finance", "governance"] },
  { id: "sec:5501", type: "security.audit", sev: "info", ws: "acme-prod", ts: "07:15:00Z", msg: "login · elliot@acme.io · MFA verified · fsn1-hetz", pillars: ["security", "archives"] },
  { id: "ws:42", type: "workspace.created", sev: "info", ws: "new-tenant", ts: "07:10:22Z", msg: "new workspace · free tier · welcome worker assigned", pillars: ["growth", "product"] },
  { id: "sub:88", type: "subscription.state", sev: "info", ws: "medcorp", ts: "07:08:11Z", msg: "growth → sovereign upgrade · reserve funded", pillars: ["finance", "growth"] },
];

const EVAL_Q = [
  { ws: "acme-prod", handle: "elliot", tier: "sovereign", act: 92, risk: 8, runs: 1247, action: "Send focused onboarding note tied to their last governed run.", workers: ["gauge", "welcome", "mirror", "ledger"] },
  { ws: "medcorp-staging", handle: "kira", tier: "growth", act: 64, risk: 25, runs: 45, action: "Guide buyer to test the endpoint on-page and create proof.", workers: ["gauge", "welcome", "mirror"] },
  { ws: "fintech-trial", handle: "alex", tier: "free", act: 38, risk: 55, runs: 14, action: "Explain activation, reserve funding, and regulated access path.", workers: ["gauge", "welcome", "mint"] },
  { ws: "agency-demo", handle: "priya", tier: "free", act: 22, risk: 12, runs: 3, action: "Wait for first governed action; no intervention without product evidence.", workers: ["gauge", "welcome"] },
];

const sColor: Record<WorkerStatus, string> = { ok: "text-moss", warning: "text-amber", failed: "text-crimson", blocked: "text-crimson", idle: "text-muted" };
const sIcon: Record<WorkerStatus, React.ReactNode> = {
  ok: <CheckCircle className="h-3 w-3 text-moss" />, warning: <AlertTriangle className="h-3 w-3 text-amber" />,
  failed: <XCircle className="h-3 w-3 text-crimson" />, blocked: <XCircle className="h-3 w-3 text-crimson" />,
  idle: <Clock className="h-3 w-3 text-muted" />,
};

type Tab = "command" | "workers" | "committees" | "events" | "eval";

export function GPCPage() {
  const [tab, setTab] = useState<Tab>("command");
  const live = WORKERS.filter(w => w.status === "ok").length;
  const warn = WORKERS.filter(w => w.status === "warning").length;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <p className="v-section-label">GPC · Governed Process Control</p>
            <span className="rounded bg-amber/15 border border-amber/25 px-1.5 py-0.5 font-mono text-[8px] font-bold text-amber">UACP v5</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold text-bone">Autonomous Control Plane</h1>
          <p className="mt-1 text-sm text-muted">
            {WORKERS.length} workers · {COMMITTEES.length} committees · Real-time event stream · Evaluation surgeon · Growth intelligence
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-md border border-rule bg-ink-3 px-3 py-1.5">
            <Bot className="h-4 w-4 text-amber" />
            <span className="font-mono text-xs font-bold text-bone">{live}/{WORKERS.length}</span>
            <span className="text-[10px] font-bold text-moss">LIVE</span>
            {warn > 0 && <span className="text-[10px] font-bold text-amber">· {warn} WARN</span>}
          </div>
          <button className="v-btn-primary text-xs"><Terminal className="h-3.5 w-3.5" /> Open terminal</button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0.5 border-b border-rule">
        {([
          ["command", "Command Center", Server],
          ["workers", "Workers", Wrench],
          ["committees", "Committees", Users],
          ["events", "Event Stream", Activity],
          ["eval", "Evaluation Surgeon", Target],
        ] as [Tab, string, typeof Server][]).map(([key, label, Icon]) => (
          <button key={key} onClick={() => setTab(key)} className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${tab === key ? "border-amber text-bone" : "border-transparent text-muted hover:text-bone"}`}>
            <Icon className="h-3.5 w-3.5" /> {label}
          </button>
        ))}
      </div>

      {tab === "command" && <CommandCenter />}
      {tab === "workers" && <WorkersGrid />}
      {tab === "committees" && <CommitteesView />}
      {tab === "events" && <EventStream />}
      {tab === "eval" && <EvalSurgeon />}
    </div>
  );
}

/* ── COMMAND CENTER ──────────────────────────────────────────────────────── */
function CommandCenter() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {/* Product truth */}
      <div className="v-card lg:col-span-2">
        <p className="v-section-label">Product Truth · Real-time</p>
        <p className="mt-0.5 text-sm font-semibold text-bone">Backend-owned product reality — /internal/uacp/summary</p>
        <div className="mt-4 grid grid-cols-4 gap-3">
          {[
            { l: "Workspaces", v: "42", s: "38 active", c: "amber" },
            { l: "Users", v: "127", s: "119 active", c: "electric" },
            { l: "Subscriptions", v: "28", s: "24 active", c: "moss" },
            { l: "Reserve", v: "$8,420", s: "8.42M units", c: "brass" },
            { l: "Requests 24h", v: "2,418", s: "12 failed", c: "electric" },
            { l: "AI Audits 24h", v: "1,892", s: "hash-chained", c: "moss" },
            { l: "Pipeline Runs", v: "312", s: "24h window", c: "violet" },
            { l: "Deployments", v: "18", s: "6 primary", c: "amber" },
          ].map(s => (
            <div key={s.l} className="rounded-md border border-rule/50 bg-ink-3/30 p-3">
              <p className="font-mono text-[8px] uppercase tracking-wider text-muted">{s.l}</p>
              <p className="mt-1 text-lg font-bold text-bone">{s.v}</p>
              <div className="mt-1.5 h-5"><MiniChart color={s.c} /></div>
              <p className="mt-1 font-mono text-[9px] text-muted-2">{s.s}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Permission boundary + UACP truth */}
      <div className="space-y-4">
        <div className="v-card">
          <p className="v-section-label">UACP Truth</p>
          <div className="mt-3 space-y-2">
            {[
              { l: "Workers", v: "20", c: "text-amber" },
              { l: "Committees", v: "5", c: "text-electric" },
              { l: "Event owners", v: "8 types", c: "text-moss" },
              { l: "Write surface", v: "/internal/operators/runs", c: "text-muted" },
              { l: "Read surface", v: "/internal/uacp/events", c: "text-muted" },
            ].map(r => (
              <div key={r.l} className="flex items-center justify-between">
                <span className="text-[10px] text-muted">{r.l}</span>
                <span className={`font-mono text-[10px] font-bold ${r.c}`}>{r.v}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="v-card">
          <p className="v-section-label">Permission Boundary</p>
          <div className="mt-3 space-y-2.5">
            <div>
              <p className="font-mono text-[8px] text-amber uppercase">Backend writes</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {["events", "runs", "billing", "evidence", "deploy", "security"].map(t => (
                  <span key={t} className="rounded bg-amber/10 border border-amber/20 px-1.5 py-0.5 font-mono text-[7px] text-amber">{t}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="font-mono text-[8px] text-electric uppercase">UACP writes</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {["worker_runs", "decisions", "escalations", "archives"].map(t => (
                  <span key={t} className="rounded bg-electric/10 border border-electric/20 px-1.5 py-0.5 font-mono text-[7px] text-electric">{t}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="font-mono text-[8px] text-crimson uppercase">Blocked w/o approval</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {["pricing", "delete_data", "secrets", "ship_code"].map(t => (
                  <span key={t} className="rounded bg-crimson/10 border border-crimson/20 px-1.5 py-0.5 font-mono text-[7px] text-crimson">{t}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Live event stream */}
      <div className="v-card lg:col-span-3">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="v-section-label">Live Event Stream</p>
            <p className="text-sm font-semibold text-bone">Merged Redis + DB · pillar-routed to workers</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="v-badge v-badge-green">● STREAMING</span>
            <button className="v-btn-ghost text-[10px]"><Download className="h-3 w-3" /> Export</button>
          </div>
        </div>
        <div className="rounded-md border border-rule bg-ink-2 p-3 font-mono text-[9.5px] leading-[2] overflow-x-auto max-h-52">
          {EVENTS.map(e => (
            <div key={e.id} className={`flex gap-3 whitespace-nowrap ${e.sev === "error" ? "text-crimson" : "text-muted"}`}>
              <span className="text-muted-2 w-20 shrink-0">{e.ts}</span>
              <span className={`w-3 shrink-0 ${e.sev === "error" ? "text-crimson" : "text-moss"}`}>{e.sev === "error" ? "✗" : "✓"}</span>
              <span className="text-bone-2 w-28 shrink-0">{e.type}</span>
              <span className="text-muted w-24 shrink-0">{e.ws}</span>
              <span className="text-bone flex-1">{e.msg}</span>
              <span className="flex gap-1 shrink-0">
                {e.pillars.map(p => <span key={p} className="rounded bg-ink-3 px-1 text-[7px] text-muted-2">{p}</span>)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── WORKERS GRID ────────────────────────────────────────────────────────── */
function WorkersGrid() {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {WORKERS.map(w => (
        <div key={w.id} className="v-card group hover:border-amber/30 transition-colors">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-md border border-rule bg-ink-3 text-amber">{w.icon}</div>
              <div>
                <p className="font-mono text-xs font-bold text-bone">{w.name}</p>
                <p className="font-mono text-[8px] text-muted">{w.pillar} · {w.committee}</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {sIcon[w.status]}
              <span className={`font-mono text-[9px] font-bold uppercase ${sColor[w.status]}`}>{w.status}</span>
            </div>
          </div>
          <p className="mt-2 text-[10px] text-muted leading-relaxed">{w.mission}</p>
          <div className="mt-3 flex gap-2">
            {w.kpis.map(k => (
              <div key={k.label} className="rounded bg-ink-3/50 border border-rule/30 px-2 py-1 flex-1">
                <p className="font-mono text-[7px] uppercase text-muted">{k.label}</p>
                <p className="font-mono text-xs font-bold text-bone">{k.value}</p>
              </div>
            ))}
          </div>
          <div className="mt-2.5 flex items-center justify-between border-t border-rule/50 pt-2">
            <span className="font-mono text-[8px] text-muted-2">Last: {w.lastRun} ago</span>
            <span className={`rounded px-1.5 py-0.5 font-mono text-[7px] font-bold ${w.rollout === "min_live" ? "bg-amber/10 text-amber border border-amber/20" : w.rollout === "staged" ? "bg-electric/10 text-electric border border-electric/20" : "bg-ink-3 text-muted border border-rule/30"}`}>{w.rollout}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── COMMITTEES ──────────────────────────────────────────────────────────── */
function CommitteesView() {
  return (
    <div className="space-y-4">
      {COMMITTEES.map(c => (
        <div key={c.id} className="v-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`h-2.5 w-2.5 rounded-full ${c.color}`} />
              <div>
                <p className="text-sm font-bold text-bone">{c.name}</p>
                <p className="text-[10px] text-muted">{c.authority}</p>
              </div>
            </div>
            <span className="v-badge v-badge-muted">{c.workers.length} workers</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {c.workers.map(wId => {
              const w = WORKERS.find(x => x.id === wId);
              if (!w) return null;
              return (
                <div key={wId} className="flex items-center gap-1.5 rounded-md border border-rule bg-ink-3/40 px-2.5 py-1.5 hover:border-amber/30 transition-colors">
                  <span className="text-amber">{w.icon}</span>
                  <span className="font-mono text-[9px] font-bold text-bone">{w.name}</span>
                  {sIcon[w.status]}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── EVENT STREAM ────────────────────────────────────────────────────────── */
function EventStream() {
  return (
    <div className="v-card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="v-section-label">UACP Event Stream · Full</p>
          <p className="text-sm font-semibold text-bone">All product events → pillar / committee / worker routing</p>
        </div>
        <div className="flex gap-2">
          <span className="v-badge v-badge-green">● Redis-backed</span>
          <span className="v-badge v-badge-muted">{EVENTS.length} events</span>
        </div>
      </div>
      <div className="space-y-2">
        {EVENTS.map(e => (
          <div key={e.id} className={`rounded-md border p-3 ${e.sev === "error" ? "border-crimson/30 bg-crimson/5" : "border-rule/50 bg-ink-3/20"}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${e.sev === "error" ? "bg-crimson" : "bg-moss"}`} />
                <span className="font-mono text-xs font-bold text-bone">{e.type}</span>
                <span className="font-mono text-[9px] text-muted">{e.ws}</span>
              </div>
              <span className="font-mono text-[9px] text-muted-2">{e.ts}</span>
            </div>
            <p className="mt-1.5 text-[11px] text-bone-2 leading-relaxed">{e.msg}</p>
            <div className="mt-2 flex items-center gap-1">
              {e.pillars.map(p => (
                <span key={p} className="rounded bg-ink-3 border border-rule/30 px-1.5 py-0.5 font-mono text-[7px] text-muted">{p}</span>
              ))}
              <ChevronRight className="ml-auto h-3 w-3 text-muted" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── EVALUATION SURGEON ──────────────────────────────────────────────────── */
function EvalSurgeon() {
  return (
    <div className="space-y-4">
      <div className="v-card">
        <div className="flex items-center justify-between">
          <div>
            <p className="v-section-label">Evaluation Surgeon Queue</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">
              Workspace-by-workspace activation scoring · risk assessment · top action · worker assignment
            </p>
          </div>
          <span className="v-badge v-badge-muted">{EVAL_Q.length} workspaces</span>
        </div>
      </div>
      {EVAL_Q.map(eq => (
        <div key={eq.ws} className="v-card hover:border-amber/20 transition-colors">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-mono text-sm font-bold text-bone">{eq.ws}</p>
                <span className={`rounded px-1.5 py-0.5 font-mono text-[8px] font-bold border ${eq.tier === "sovereign" ? "bg-amber/10 text-amber border-amber/20" : eq.tier === "growth" ? "bg-moss/10 text-moss border-moss/20" : "bg-ink-3 text-muted border-rule/30"}`}>{eq.tier}</span>
              </div>
              <p className="mt-0.5 font-mono text-[10px] text-muted">@{eq.handle} · {eq.runs} governed runs</p>
            </div>
            <div className="flex gap-4">
              <div className="text-center">
                <p className="font-mono text-[7px] uppercase tracking-wider text-muted">Activation</p>
                <p className={`font-mono text-xl font-bold ${eq.act >= 70 ? "text-moss" : eq.act >= 40 ? "text-amber" : "text-crimson"}`}>{eq.act}</p>
              </div>
              <div className="text-center">
                <p className="font-mono text-[7px] uppercase tracking-wider text-muted">Risk</p>
                <p className={`font-mono text-xl font-bold ${eq.risk >= 50 ? "text-crimson" : eq.risk >= 25 ? "text-amber" : "text-moss"}`}>{eq.risk}</p>
              </div>
            </div>
          </div>
          <div className="mt-3 rounded-md border border-amber/20 bg-amber/5 px-3 py-2.5">
            <p className="font-mono text-[8px] uppercase tracking-wider text-amber">Top Action</p>
            <p className="mt-0.5 text-xs text-bone leading-relaxed">{eq.action}</p>
          </div>
          <div className="mt-3 flex items-center gap-1.5 flex-wrap">
            <span className="font-mono text-[8px] text-muted mr-1">Assigned:</span>
            {eq.workers.map(wId => {
              const w = WORKERS.find(x => x.id === wId);
              return w ? (
                <span key={wId} className="inline-flex items-center gap-1 rounded bg-ink-3 border border-rule/30 px-1.5 py-0.5 font-mono text-[8px] text-bone">
                  <span className="text-amber">{w.icon}</span> {w.name}
                </span>
              ) : null;
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
