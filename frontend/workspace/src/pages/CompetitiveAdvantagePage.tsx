import type { ComponentType } from "react";
import {
  ArrowRight,
  BadgeCheck,
  BrainCircuit,
  CircuitBoard,
  DollarSign,
  FileCheck2,
  GitBranch,
  Hash,
  Landmark,
  LineChart,
  Lock,
  Network,
  OctagonAlert,
  PlugZap,
  Scale,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Workflow,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/cn";

// ─── Static data ────────────────────────────────────────────────────────────

const PILLARS = [
  {
    id: "cost",
    title: "Cost Intelligence Engine",
    label: "Provable savings",
    icon: DollarSign,
    tone: "stable" as const,
    summary: "Real-time cost prediction before execution. Intelligent routing that saves 30–70% without quality loss. Precise to the cent.",
    claims: [
      { stat: "95%", detail: "prediction accuracy within 5%" },
      { stat: "30–70%", detail: "routing savings vs single provider" },
      { stat: "¢-precise", detail: "billing allocation per client" },
    ],
    proof: "Enterprises can prove ROI. Agencies bill accurately. No one else offers this in BYOS form.",
    to: "/billing",
  },
  {
    id: "compliance",
    title: "Compliance That Actually Works",
    label: "Cryptographic proof",
    icon: FileCheck2,
    tone: "stable" as const,
    summary: "HMAC-SHA256 audit logs that cannot be modified after creation. Auditors can verify every entry. GDPR, CCPA, SOC2-ready reports.",
    claims: [
      { stat: "HMAC-SHA256", detail: "cryptographically verifiable logs" },
      { stat: "Immutable", detail: "cannot be modified after signing" },
      { stat: "Auto-PII", detail: "detection and masking built-in" },
    ],
    proof: "Enterprises can prove compliance. Auditors can verify. No one else offers cryptographic verification.",
    to: "/compliance",
  },
  {
    id: "security",
    title: "Security Leadership",
    label: "Zero-trust architecture",
    icon: ShieldCheck,
    tone: "stable" as const,
    summary: "Verify every request. Encryption at rest and in transit. Secrets management with rotation support. Abuse prevention with anomaly detection.",
    claims: [
      { stat: "Zero-trust", detail: "every request verified" },
      { stat: "End-to-end", detail: "encryption at rest and in transit" },
      { stat: "Anomaly", detail: "detection and rate limiting" },
    ],
    proof: "Enterprise-grade security that enterprises actually trust.",
    to: "/settings",
  },
  {
    id: "privacy",
    title: "Privacy-by-Design",
    label: "GDPR out of the box",
    icon: Lock,
    tone: "stable" as const,
    summary: "Privacy built from day one, not bolted on. Automatic PII detection and masking. Data minimization. Automatic deletion after retention period.",
    claims: [
      { stat: "Day-one", detail: "privacy built into the architecture" },
      { stat: "Auto-mask", detail: "PII detection on every request" },
      { stat: "GDPR rights", detail: "access, deletion, portability" },
    ],
    proof: "GDPR compliance out of the box. Competitors retrofit it. We architected it.",
    to: "/compliance",
  },
  {
    id: "futureproof",
    title: "Future-Proof Architecture",
    label: "Adapts to change",
    icon: PlugZap,
    tone: "neutral" as const,
    summary: "Plugin system for new providers. Swap providers in under a day. Add new regulations in under a week. Zero breaking changes for tenants.",
    claims: [
      { stat: "< 1 day", detail: "provider swap time" },
      { stat: "< 1 week", detail: "new regulation support" },
      { stat: "Zero", detail: "breaking changes for tenants" },
    ],
    proof: "Adapts to change. Doesn't become obsolete. Competitors lock you in.",
    to: "/settings",
  },
];

const MARKET_SEGMENTS = [
  {
    segment: "Agencies",
    tagline: "Bill clients accurately. Never eat costs again.",
    icon: DollarSign,
    tone: "stable" as const,
    advantages: [
      "Cost allocation per project and client",
      "Precise billing — no guessing, no rounding",
      "Markup support for margin",
      "Prove value with cost transparency reports",
    ],
  },
  {
    segment: "Enterprises",
    tagline: "Prove compliance. Control costs automatically.",
    icon: Landmark,
    tone: "stable" as const,
    advantages: [
      "GDPR-compliant audit trails — cryptographically verified",
      "30–70% cost optimization with budget enforcement",
      "Zero-trust security with full audit logging",
      "Privacy-by-design — not a compliance checkbox",
    ],
  },
  {
    segment: "Developers",
    tagline: "Know costs before you build. Optimize automatically.",
    icon: CircuitBoard,
    tone: "neutral" as const,
    advantages: [
      "Cost prediction before any operation runs",
      "Intelligent routing — automatic optimization",
      "Provider abstraction — swap without code changes",
      "Plugin system — extend without touching core",
    ],
  },
];

const DIFFERENTIATORS = [
  {
    label: "Cost prediction accuracy",
    value: "95% within 5%",
    icon: LineChart,
    detail: "Measurable, not estimates. Tracked against actuals. Improves over time.",
  },
  {
    label: "Routing savings range",
    value: "30–70%",
    icon: TrendingDown,
    detail: "Logged, auditable, A/B tested. No quality degradation below threshold.",
  },
  {
    label: "Audit log integrity",
    value: "HMAC-SHA256",
    icon: Hash,
    detail: "Cryptographically verifiable. Immutable. Passes external audits.",
  },
  {
    label: "Billing precision",
    value: "Cent-accurate",
    icon: BadgeCheck,
    detail: "No rounding errors. Every allocation traceable. Invoice-ready output.",
  },
  {
    label: "Provider swap time",
    value: "< 1 day",
    icon: GitBranch,
    detail: "Plugin architecture. Zero tenant breaking changes. Zero lock-in.",
  },
  {
    label: "Regulation onboarding",
    value: "< 1 week",
    icon: Scale,
    detail: "Regulatory framework with version support. Add rules without core changes.",
  },
];

const KILLER_FEATURES = [
  {
    title: "Cost Prediction",
    detail: "Know costs before committing. 95% accuracy within 5%.",
    icon: Sparkles,
  },
  {
    title: "Intelligent Routing",
    detail: "Automatically optimize provider selection. Save 30–70%.",
    icon: Network,
  },
  {
    title: "Audit Trail",
    detail: "Cryptographic proof of every decision. Immutable lineage.",
    icon: Workflow,
  },
];

// ─── Page ────────────────────────────────────────────────────────────────────

export function CompetitiveAdvantagePage() {
  return (
    <div className="command-wall">
      <AdvantageHeader />
      <KillerFeatureBanner />

      <section className="sv-chamber">
        <SectionTitle
          eyebrow="The five pillars"
          title="What we do differently"
          text="No other BYOS backend combines cost intelligence, cryptographic compliance, zero-trust security, privacy-by-design, and future-proof architecture in a single governed platform."
        />
        <PillarGrid />
      </section>

      <section className="sv-chamber">
        <SectionTitle
          eyebrow="Precision and accuracy"
          title="The proof layer"
          text="We don't claim savings. We measure, log, and prove them. Every prediction, routing decision, audit entry, and billing line is tracked against actuals."
        />
        <DifferentiatorGrid />
      </section>

      <section className="sunnyvale-floor">
        <SectionTitle
          eyebrow="Market positioning"
          title="Who wins with this"
          text="The platform is purpose-built for three audiences. Each gets a distinct, provable value from the same governed infrastructure."
        />
        <SegmentWall />
      </section>

      <PositioningFooter />
    </div>
  );
}

// ─── Header ──────────────────────────────────────────────────────────────────

function AdvantageHeader() {
  return (
    <header className="command-header">
      <div>
        <div className="command-kicker">Competitive doctrine</div>
        <h1>The only secure, future-proof, cost-intelligent AI backend</h1>
        <p>
          BYOS — Bring Your Own Sovereign stack. Five provable advantages. Zero lock-in.
        </p>
      </div>
      <div className="command-status-strip">
        <StatusDatum label="Unique position" value="BYOS cost intelligence" tone="stable" />
        <StatusDatum label="Compliance posture" value="Cryptographic proof" tone="stable" />
        <StatusDatum label="Security model" value="Zero-trust by default" tone="stable" />
        <StatusDatum label="Architecture" value="Future-proof, plugin-native" tone="neutral" />
      </div>
    </header>
  );
}

// ─── Killer feature banner ───────────────────────────────────────────────────

function KillerFeatureBanner() {
  return (
    <section className="command-bridge" aria-label="Killer feature triptych">
      <div className="bridge-prime">
        <span>The killer combination</span>
        <h2>The only AI backend that makes you money instead of costing you money</h2>
        <p>
          No competitor combines all three. Cost prediction before execution, intelligent routing that
          automatically optimizes, and a cryptographic audit trail that proves compliance. Together,
          these three capabilities form the unique selling proposition that no incumbent can
          replicate without rebuilding from scratch.
        </p>
        <div className="bridge-pulse">
          <i />
          <b>Sovereign by architecture</b>
          <small>Own your stack — no vendor lock-in, no shared data plane, no surprise bills</small>
        </div>
      </div>
      <div className="bridge-actions">
        {KILLER_FEATURES.map((feature) => (
          <div key={feature.title} className="bridge-action" style={{ cursor: "default" }}>
            <feature.icon className="h-4 w-4" />
            <span>{feature.title}</span>
            <b>Proven</b>
            <small>{feature.detail}</small>
            <Zap className="bridge-arrow h-3.5 w-3.5" />
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Pillar grid ─────────────────────────────────────────────────────────────

function PillarGrid() {
  return (
    <div className="sv-grid">
      {PILLARS.map((pillar) => (
        <PillarPanel key={pillar.id} pillar={pillar} />
      ))}
    </div>
  );
}

function PillarPanel({ pillar }: { pillar: typeof PILLARS[number] }) {
  return (
    <div className={cn("mineral-panel sv-prime", pillar.tone)}>
      <PanelChrome label={pillar.label} icon={pillar.icon} />
      <div className="state-core">
        <div className={cn("state-orbit", pillar.tone)}>
          <span />
          <b>{pillar.title.split(" ").slice(-1)[0].toUpperCase()}</b>
        </div>
        <div>
          <h3>{pillar.title}</h3>
          <p>{pillar.summary}</p>
        </div>
      </div>
      <div className="state-matrix">
        {pillar.claims.map((claim) => (
          <div key={claim.stat} className="signal-readout">
            <BadgeCheck className="h-3.5 w-3.5" />
            <span>{claim.detail}</span>
            <b>{claim.stat}</b>
          </div>
        ))}
      </div>
      <div className="panel-chrome" style={{ marginTop: "var(--space-3)", borderTop: "1px solid var(--color-divider)", paddingTop: "var(--space-3)" }}>
        <span style={{ color: "var(--color-text-muted)", fontSize: "var(--text-xs)" }}>
          <ShieldCheck className="h-3 w-3" style={{ display: "inline", marginRight: "4px" }} />
          {pillar.proof}
        </span>
      </div>
      <a href={pillar.to} className="bridge-action" style={{ marginTop: "var(--space-2)" }}>
        <ArrowRight className="h-3.5 w-3.5" />
        <span>Explore in platform</span>
        <ArrowRight className="bridge-arrow h-3.5 w-3.5" />
      </a>
    </div>
  );
}

// ─── Differentiator grid ─────────────────────────────────────────────────────

function DifferentiatorGrid() {
  return (
    <div className="sunnyvale-grid">
      {DIFFERENTIATORS.map((item) => (
        <div key={item.label} className="mineral-panel">
          <PanelChrome label={item.label} icon={item.icon} />
          <div className="committee-score">
            <span>Proven metric</span>
            <b>{item.value}</b>
            <small>{item.detail}</small>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Segment wall ────────────────────────────────────────────────────────────

function SegmentWall() {
  return (
    <div className="sv-grid">
      {MARKET_SEGMENTS.map((seg) => (
        <div key={seg.segment} className={cn("mineral-panel sv-trajectory", seg.tone)}>
          <PanelChrome label={`For ${seg.segment}`} icon={seg.icon} />
          <div className="trajectory-bands">
            <div className="committee-score">
              <span>{seg.segment}</span>
              <b style={{ fontSize: "var(--text-base)" }}>{seg.tagline}</b>
            </div>
          </div>
          <div className="session-list">
            {seg.advantages.map((adv) => (
              <div key={adv} className="session-row">
                <BadgeCheck className="h-3.5 w-3.5" />
                <div>
                  <b>{adv}</b>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Footer positioning strip ─────────────────────────────────────────────────

function PositioningFooter() {
  const pillars = [
    { label: "Independence", detail: "Own your stack — no lock-in", icon: GitBranch },
    { label: "Savings", detail: "Prove you save money", icon: TrendingDown },
    { label: "Compliance", detail: "Prove you're compliant", icon: FileCheck2 },
    { label: "Security", detail: "Prove you're secure", icon: ShieldCheck },
    { label: "Future", detail: "Prove you're future-proof", icon: PlugZap },
  ];

  return (
    <section className="archives-spine">
      <div>
        <div className="archive-mark">
          <BrainCircuit className="h-4 w-4" /> Positioning doctrine
        </div>
        <h2>Built to lead. Designed to last. Proven to work.</h2>
        <p>
          We're not selling features. We're selling independence, savings, compliance, security, and
          a future-proof architecture — each with provable, measurable evidence baked into the
          platform itself.
        </p>
      </div>
      <div className="archive-line">
        {pillars.map((p) => (
          <div key={p.label}>
            <b>
              <p.icon
                className="h-3.5 w-3.5"
                style={{ display: "inline", marginRight: "6px" }}
              />
              {p.label}
            </b>
            <span>{p.detail}</span>
            <OctagonAlert className="h-3 w-3" style={{ opacity: 0 }} />
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Shared primitives ────────────────────────────────────────────────────────

function PanelChrome({
  label,
  icon: Icon,
}: {
  label: string;
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="panel-chrome">
      <span>
        <Icon className="h-3.5 w-3.5" /> {label}
      </span>
    </div>
  );
}

function SectionTitle({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="command-section-title">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}

function StatusDatum({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "stable" | "watch" | "critical" | "neutral";
}) {
  return (
    <div className={cn("status-datum", tone)}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}
