import { useState, useEffect, useCallback } from "react";
import { Search, Filter, Star, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";

const CATEGORIES = ["All", "Models", "Pipelines", "RAG Templates", "Prompt Packs", "Compliance Packs", "Connectors", "SDK Extensions", "Deployment Images", "Managed Services"];

const FEATURED = [
  { title: "Clinical-RAG · HIPAA Pack", vendor: "Veklom Native", desc: "PHI-safe RAG over clinical PDFs with redaction, chunking, audit trail, and signed evidence export.", tags: ["HIPAA", "SOC2"], badge: "HIPAA-Ready", infra: "Hetzner", type: "Container", price: "$1,490 / mo", installs: "218", rating: "4.9", featured: true, category: "RAG Templates" },
  { title: "PCI-DSS v4 Compliance Pack", vendor: "Veklom Native", desc: "Pre-wired control mappings, evidence schedule, and tamper-evident export bundles for PCI-DSS v4.", tags: ["PCI", "SOC2"], badge: "Auditor-Signed", infra: "Hetzner + AWS", type: "Managed", price: "$2,400 / mo", installs: "73", rating: "5", featured: true, category: "Compliance Packs" },
];

const LISTINGS = [
  { title: "Clinical-RAG · HIPAA Pack", vendor: "Veklom Native", desc: "PHI-safe RAG over clinical PDFs with redaction, chunking, audit trail, and signed evidence export.", tags: ["HIPAA", "SOC2"], badge: "HIPAA-Ready", infra: "Hetzner", type: "Container", price: "$1,490 / mo", rating: "4.9", category: "RAG Templates" },
  { title: "Legal Redactor + Diff Engine", vendor: "Stelos Labs", desc: "Strip PII, redline contracts, and emit signed redaction reports without leaving your perimeter.", tags: ["GDPR", "SOC2"], badge: "PII-Strip", infra: "Hetzner + AWS", type: "Container", price: "$890 / mo", rating: "4.8", category: "Pipelines" },
  { title: "Qwen 2.5 72B · INT4 Image", vendor: "Veklom Native", desc: "Pre-quantized GGUF image tuned for 8×A100 Hetzner GPU pools. Deploy in under 90 seconds.", tags: ["SOC2"], badge: "INT4 GGUF", infra: "Hetzner", type: "", price: "Free", rating: "4.7", category: "Deployment Images" },
  { title: "PCI-DSS v4 Compliance Pack", vendor: "Veklom Native", desc: "Pre-wired control mappings, evidence schedule, and tamper-evident export bundles for PCI-DSS v4.", tags: ["PCI", "SOC2"], badge: "PCI-DSS v4", infra: "Hetzner + AWS", type: "Managed", price: "$2,400 / mo", rating: "5", category: "Compliance Packs" },
  { title: "Okta SCIM Connector", vendor: "Bridgekeeper", desc: "SCIM 2.0 + SAML provisioning into Veklom Team with automated role mapping and de-provisioning audits.", tags: ["SOC2"], badge: "SCIM 2.0 SAML", infra: "Hetzner + AWS", type: "Hosted", price: "$240 / mo", rating: "4.6", category: "Connectors" },
  { title: "Finance Prompt Pack", vendor: "Numera", desc: "62 production-grade prompts for financial summaries, risk flags, and disclosure drafting.", tags: ["SOC2"], badge: "Versioned Diff-Ready", infra: "Hetzner + AWS", type: "SDK", price: "$179 one-time", rating: "4.4", category: "Prompt Packs" },
  { title: "Veklom On-Call · Managed", vendor: "Veklom Native", desc: "24/7 SRE on-call for your Veklom estate. Deploy review, GPU re-balancing, and audit prep included.", tags: ["SOC2", "HIPAA"], badge: "24/7 SLD-Backed", infra: "Hetzner + AWS", type: "Managed", price: "$6,800 / mo", rating: "4.9", category: "Managed Services" },
  { title: "Veklom Python SDK Pro", vendor: "Veklom Native", desc: "Typed clients with auto-failover, in-flight redaction, and OpenTelemetry baked in.", tags: [], badge: "Typed Open Source", infra: "Hetzner + AWS", type: "SDK", price: "Free", rating: "4.8", category: "SDK Extensions" },
  { title: "MedDx-Triage 13B", vendor: "Northern Health", desc: "PHI-aware triage model fine-tuned on 1.4M de-identified intake notes. License-bound, watermarked.", tags: ["HIPAA"], badge: "PHI-Aware Watermarked", infra: "Hetzner", type: "Container", price: "$3,200 / mo", rating: "4.7", category: "Models" },
  { title: "EU-Sovereign Residency Pack", vendor: "Veklom Native", desc: "Region-pinning, policy templates, and procurement letter generator for EU-sovereign deployments.", tags: ["GDPR", "SOC2"], badge: "EU-Only Procurement-Ready", infra: "Hetzner", type: "Managed", price: "$1,100 / mo", rating: "4.9", category: "Compliance Packs" },
];

export function MarketplacePage() {
  const [listings, setListings] = useState(LISTINGS);
  const [liveCount, setLiveCount] = useState<number | null>(null);

  const fetchListings = useCallback(async () => {
    try {
      const { data } = await api.get("/marketplace/listings");
      const items = Array.isArray(data) ? data : data?.listings || data?.items || [];
      if (items.length > 0) {
        setListings(items);
        setLiveCount(items.length);
      }
    } catch { /* use static fallback */ }
  }, []);

  useEffect(() => { fetchListings(); }, [fetchListings]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Marketplace</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Sovereign-ready assets, governed distribution</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Models, pipelines, compliance packs, connectors, and managed services — every listing inherits Veklom's policy engine and audit trail.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <span className="rounded bg-amber/15 px-2 py-0.5 font-mono text-[9px] font-semibold text-amber">License-Bound · Watermarked · Signed</span>
            <span className="font-mono text-[10px] text-muted">{liveCount ?? listings.length} Listings</span>
            <span className="font-mono text-[10px] text-muted">52 Verified Providers</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone hover:border-muted transition-colors">
            My purchases
          </button>
          <button className="v-btn-primary text-xs">Become a provider</button>
        </div>
      </div>

      {/* Featured */}
      <div className="grid gap-4 md:grid-cols-2">
        {FEATURED.map((item) => (
          <div key={item.title} className="relative overflow-hidden rounded-lg border border-brass/30 bg-gradient-to-br from-ink-2 to-ink-3 p-5">
            <div className="mb-2 flex items-center gap-2">
              <span className="v-badge-amber">★ Featured</span>
              <span className="font-mono text-[9px] uppercase text-muted">{item.category}</span>
              <span className="font-mono text-[9px] text-muted">· {item.vendor}</span>
            </div>
            <h3 className="text-lg font-bold text-bone">{item.title}</h3>
            <p className="mt-1 text-xs text-muted leading-relaxed">{item.desc}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {item.tags.map((t) => (
                <span key={t} className="rounded bg-amber/15 px-1.5 py-0.5 font-mono text-[9px] text-amber">{t}</span>
              ))}
              <span className="rounded bg-ink-3 px-1.5 py-0.5 font-mono text-[9px] text-muted">{item.badge}</span>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <div>
                <span className="text-lg font-bold text-bone">{item.price}</span>
                <span className="ml-2 font-mono text-[10px] text-muted">{item.installs} installs · ★ {item.rating}</span>
              </div>
              <button className="v-btn-ghost text-xs">View listing <ExternalLink className="h-3 w-3" /></button>
            </div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input type="text" placeholder="Search listings, providers, compliance frameworks..." className="v-input pl-10" />
        </div>
        <button className="v-btn-ghost"><Filter className="h-4 w-4" /> Filters</button>
      </div>

      {/* Categories */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat, i) => (
          <button key={cat} className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${i === 0 ? "bg-brass/15 text-brass-2 border border-brass/30" : "border border-rule text-muted hover:text-bone hover:border-muted"}`}>
            {cat}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {LISTINGS.map((item) => (
          <div key={item.title} className="v-card flex flex-col">
            <div className="mb-2 flex items-center gap-2 text-[10px]">
              <span className="font-mono uppercase text-muted">{item.category}</span>
              <span className="text-muted-2">·</span>
              <span className="text-muted">{item.vendor}</span>
              <span className="ml-auto flex items-center gap-0.5 text-amber">
                <Star className="h-2.5 w-2.5 fill-current" /> {item.rating}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-bone">{item.title}</h3>
            <p className="mt-1 flex-1 text-[11px] leading-relaxed text-muted">{item.desc}</p>
            <div className="mt-3 flex flex-wrap gap-1">
              {item.tags.map((t) => (
                <span key={t} className="rounded bg-amber/15 px-1.5 py-0.5 font-mono text-[8px] text-amber">{t}</span>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between border-t border-rule pt-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[9px] text-muted">{item.infra}</span>
                {item.type && <span className="font-mono text-[9px] text-muted-2">{item.type}</span>}
              </div>
              <span className="font-mono text-xs font-semibold text-bone">{item.price} <ExternalLink className="inline h-2.5 w-2.5" /></span>
            </div>
          </div>
        ))}
      </div>

      {/* Governance bar */}
      <div className="grid grid-cols-2 gap-4 rounded-lg border border-rule bg-ink-2/50 p-4 md:grid-cols-4">
        {[
          { icon: "📦", title: "Governed packaging", desc: "Hosted APIs · containers · CLI · SDK · signed builds." },
          { icon: "🔐", title: "License-bound", desc: "Activation, account binding, watermarking, metering, expiry." },
          { icon: "✓", title: "Vetted providers", desc: "Identity verified · signed builds · evidence-linked." },
          { icon: "💳", title: "One bill", desc: "Marketplace charges roll into your Veklom invoice." },
        ].map((item) => (
          <div key={item.title} className="flex items-start gap-2.5">
            <span className="text-sm">{item.icon}</span>
            <div>
              <p className="text-xs font-semibold text-bone">{item.title}</p>
              <p className="mt-0.5 text-[10px] leading-relaxed text-muted">{item.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
