import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Flame,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  Store,
  Tag,
  X,
  Zap,
} from "lucide-react";
import { PlatformPulseSection } from "@/components/overview/PlatformPulseSection";
import { api } from "@/lib/api";
import { fmtCents, cn } from "@/lib/cn";
import { ProofStrip, RunStatePanel } from "@/components/workspace/FlowPrimitives";

interface ListingCard {
  id: string;
  slug?: string | null;
  title: string;
  provider?: string | null;
  summary?: string | null;
  listing_type: string;
  category?: string | null;
  tags: string[];
  compliance_badges: string[];
  price_cents: number;
  currency: string;
  predicted_cost_per_run_usd?: number | null;
  rating_avg: number;
  rating_count: number;
  install_count: number;
  is_featured: boolean;
  source_url?: string | null;
  use_url?: string | null;
  source_verified: boolean;
  verification_note?: string | null;
  billing?: string | null;
  usage?: string | null;
}

interface FeaturedResp {
  featured: ListingCard[];
  trending: ListingCard[];
  new: ListingCard[];
}

interface CategoriesResp {
  categories: { slug: string; count: number }[];
  types: { slug: string; count: number }[];
}

interface Preflight {
  listing_id: string;
  predicted_cost_per_run_usd: number;
  confidence_lower_usd: number;
  confidence_upper_usd: number;
  predicted_quality?: number | null;
  failure_risk?: number | null;
  alternative_providers: { provider: string; cost: string; savings_percent: number }[];
  compliance_badges: string[];
}

interface MarketplaceOrder {
  id: string;
  status: string;
  total_cents: number;
  currency: string;
  created_at: string;
  items: Array<{
    id: string;
    listing_id: string;
    listing_title?: string | null;
    price_cents: number;
    status: string;
  }>;
}

const TYPE_LABEL: Record<string, string> = {
  pipeline: "Pipeline",
  tool: "Tool",
  prompt_pack: "Prompt pack",
  dataset: "Dataset",
  agent: "Agent",
  connector: "Connector",
  evidence_pack: "Evidence pack",
  edge_template: "Edge template",
};

const CATEGORY_LABEL: Record<string, string> = {
  legal: "Legal",
  medical: "Medical",
  finance: "Finance",
  compliance: "Compliance",
  infra: "Infrastructure",
  edge_industrial: "Edge / Industrial",
  agency: "Agency",
  general: "General",
  "sdk-extensions": "SDK Extensions",
  connectors: "Connectors",
  "compliance-packs": "Compliance Packs",
  "deployment-images": "Deployment Images",
  "managed-services": "Managed Services",
  pipelines: "Pipelines",
};

async function fetchFeatured(): Promise<FeaturedResp> {
  const r = await api.get<unknown>("/marketplace/listings", { params: { limit: 50 } });
  const cards = normalizeListings(r.data);
  const featured = cards.filter((card) => card.is_featured).slice(0, 8);
  const trending = [...cards]
    .filter((card) => card.source_verified)
    .sort((a, b) => Number(b.is_featured) - Number(a.is_featured) || a.title.localeCompare(b.title))
    .slice(0, 8);
  return {
    featured: featured.length ? featured : cards.slice(0, 4),
    trending,
    new: cards.slice(0, 8),
  };
}

async function fetchCategories(): Promise<CategoriesResp> {
  const r = await api.get<unknown>("/marketplace/categories");
  return normalizeCategories(r.data);
}

async function fetchPreflight(listingId: string): Promise<Preflight> {
  const r = await api.get<Preflight>(`/marketplace/listings/${listingId}/preflight`);
  return r.data;
}

async function fetchMyOrders(): Promise<MarketplaceOrder[]> {
  const r = await api.get<{ items: MarketplaceOrder[] }>("/marketplace/orders/me", { params: { limit: 25 } });
  return r.data.items ?? [];
}

function normalizeListings(data: unknown): ListingCard[] {
  const raw = Array.isArray(data)
    ? data
    : ((data as { items?: unknown[]; listings?: unknown[] })?.items ??
      (data as { items?: unknown[]; listings?: unknown[] })?.listings ??
      []);
  return raw.map(normalizeListing).filter((listing) => listing.id && listing.title);
}

function normalizeListing(raw: unknown): ListingCard {
  const row = raw as Record<string, unknown>;
  const category = slugify(String(row.category ?? "general"));
  const inferredType = inferListingType(category, String(row.install ?? ""));
  const tags = arrayOfStrings(row.tags ?? row.target ?? []);
  const badges = arrayOfStrings(row.compliance_badges ?? row.compliance ?? row.badges ?? []);
  const ratingCount = Number(row.rating_count ?? 0);
  const rating = ratingCount > 0 ? Number(row.rating_avg ?? row.rating ?? 0) : 0;
  const installs = Number(row.install_count ?? 0);

  return {
    id: String(row.id ?? row.slug ?? row.title ?? ""),
    slug: row.slug ? String(row.slug) : String(row.id ?? ""),
    title: String(row.title ?? row.name ?? ""),
    provider: row.provider ? String(row.provider) : null,
    summary: row.summary ? String(row.summary) : String(row.description ?? row.positioning ?? ""),
    listing_type: String(row.listing_type ?? inferredType),
    category,
    tags,
    compliance_badges: badges,
    price_cents: Number(row.price_cents ?? 0),
    currency: String(row.currency ?? "usd"),
    predicted_cost_per_run_usd: row.predicted_cost_per_run_usd != null ? Number(row.predicted_cost_per_run_usd) : null,
    rating_avg: rating,
    rating_count: ratingCount,
    install_count: installs,
    is_featured: Boolean(row.is_featured ?? row.featured),
    source_url: row.source_url ? String(row.source_url) : null,
    use_url: row.use_url ? String(row.use_url) : row.source_url ? String(row.source_url) : null,
    source_verified: Boolean(row.source_verified ?? row.source_url),
    verification_note: row.verification_note ? String(row.verification_note) : null,
    billing: row.billing ? String(row.billing) : null,
    usage: row.usage ? String(row.usage) : null,
  };
}

function normalizeCategories(data: unknown): CategoriesResp {
  if (!Array.isArray(data)) {
    const shaped = data as Partial<CategoriesResp> | undefined;
    return {
      categories: shaped?.categories ?? [],
      types: shaped?.types ?? [],
    };
  }
  const categories = data
    .filter((row) => {
      const id = String((row as { id?: unknown }).id ?? "");
      return id !== "all" && id !== "paid" && id !== "free";
    })
    .map((row) => ({
      slug: String((row as { id?: unknown }).id ?? (row as { slug?: unknown }).slug ?? ""),
      count: Number((row as { count?: unknown }).count ?? 0),
    }))
    .filter((row) => row.slug);
  return {
    categories,
    types: [],
  };
}

function inferListingType(category: string, install: string): string {
  const c = category.toLowerCase();
  const i = install.toLowerCase();
  if (c.includes("pipeline")) return "pipeline";
  if (c.includes("connector") || i.includes("docker") || i.includes("github")) return "connector";
  if (c.includes("compliance")) return "evidence_pack";
  if (c.includes("deployment")) return "tool";
  return "tool";
}

function arrayOfStrings(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "general";
}

function apiErrorMessage(error: unknown): string {
  const e = error as { response?: { data?: { detail?: string } }; message?: string };
  return e.response?.data?.detail ?? e.message ?? "Request failed";
}

export function MarketplacePage() {
  const { slug } = useParams();
  const [query, setQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selected, setSelected] = useState<ListingCard | null>(null);
  const [showOrders, setShowOrders] = useState(false);
  const [showProvider, setShowProvider] = useState(false);
  const [providerName, setProviderName] = useState("");

  const featuredQ = useQuery({ queryKey: ["mkt-featured"], queryFn: fetchFeatured });
  const categoriesQ = useQuery({ queryKey: ["mkt-categories"], queryFn: fetchCategories });
  const ordersQ = useQuery({ queryKey: ["mkt-orders-me"], queryFn: fetchMyOrders, enabled: showOrders });
  const preflightQ = useQuery({
    queryKey: ["mkt-preflight", selected?.id],
    queryFn: () => fetchPreflight(selected!.id),
    enabled: !!selected,
  });

  const providerMut = useMutation({
    mutationFn: async (displayName: string) => {
      await api.post("/marketplace/vendors/create", { display_name: displayName.trim() });
      const r = await api.post<{ onboarding_url?: string }>("/marketplace/vendors/onboard", {});
      return r.data;
    },
    onSuccess: (data) => {
      if (data.onboarding_url) window.location.href = data.onboarding_url;
    },
  });

  const checkoutMut = useMutation({
    mutationFn: async (id: string) => {
      const r = await api.post<{ checkout_url: string; order_id?: string }>(
        "/marketplace/payments/create-checkout",
        {
          listing_id: id,
          success_url: window.location.href,
          cancel_url: window.location.href,
        },
      );
      return r.data;
    },
    onSuccess: (data) => {
      if (data.checkout_url) window.location.href = data.checkout_url;
    },
  });

  const allCards = useMemo<ListingCard[]>(() => {
    const seen = new Set<string>();
    const merged: ListingCard[] = [];
    for (const card of [
      ...(featuredQ.data?.featured ?? []),
      ...(featuredQ.data?.trending ?? []),
      ...(featuredQ.data?.new ?? []),
    ]) {
      if (!seen.has(card.id)) {
        seen.add(card.id);
        merged.push(card);
      }
    }
    return merged;
  }, [featuredQ.data]);

  const typeFilters = useMemo(() => {
    const counts = new Map<string, number>();
    for (const card of allCards) {
      counts.set(card.listing_type, (counts.get(card.listing_type) ?? 0) + 1);
    }
    const fallback = categoriesQ.data?.types ?? [];
    const source = counts.size
      ? [...counts.entries()].map(([slug, count]) => ({ slug, count }))
      : fallback.filter((row) => row.count > 0);
    const priority = ["pipeline", "tool", "connector", "evidence_pack", "agent", "prompt_pack", "dataset", "edge_template"];
    return source.sort((a, b) => {
      const ai = priority.indexOf(a.slug);
      const bi = priority.indexOf(b.slug);
      if (ai !== -1 || bi !== -1) return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
      return a.slug.localeCompare(b.slug);
    });
  }, [allCards, categoriesQ.data?.types]);

  const categoryFilters = useMemo(() => {
    const counts = new Map<string, number>();
    for (const card of allCards) {
      counts.set(card.category ?? "general", (counts.get(card.category ?? "general") ?? 0) + 1);
    }
    if (counts.size) {
      return [...counts.entries()]
        .map(([slug, count]) => ({ slug, count }))
        .sort((a, b) => a.slug.localeCompare(b.slug));
    }
    return categoriesQ.data?.categories ?? [];
  }, [allCards, categoriesQ.data?.categories]);

  const filteredAll = useMemo(() => {
    return allCards.filter((c) => {
      if (selectedType && c.listing_type !== selectedType) return false;
      if (selectedCategory && c.category !== selectedCategory) return false;
      if (query) {
        const q = query.toLowerCase();
        const blob = `${c.title} ${c.summary ?? ""} ${(c.tags ?? []).join(" ")}`.toLowerCase();
        if (!blob.includes(q)) return false;
      }
      return true;
    });
  }, [allCards, selectedType, selectedCategory, query]);

  useEffect(() => {
    if (!slug || !allCards.length) return;
    const match = allCards.find((card) => card.slug === slug || card.id === slug);
    if (match && selected?.id !== match.id) {
      setSelected(match);
    }
  }, [allCards, selected?.id, slug]);

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Marketplace
          </div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            Sovereign-ready assets, governed distribution
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-bone-2">
            Source-verified actions, connectors, compliance packs, and managed services that can be wrapped by
            Veklom's policy engine and audit trail. Native pipeline templates live in Pipelines.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" /> live ·{" "}
              <span className="font-mono">/api/v1/marketplace</span>
            </span>
            <span className="v-chip v-chip-brass">
              <ShieldCheck className="h-3 w-3" />
              License-bound
            </span>
            <span className="v-chip">{allCards.length} listings</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="v-btn-ghost h-8 px-3 text-xs" onClick={() => setShowOrders(true)}>
            <Store className="h-3.5 w-3.5" /> My purchases
          </button>
          <button className="v-btn-primary h-8 px-3 text-xs" onClick={() => setShowProvider(true)}>
            <Sparkles className="h-3.5 w-3.5" /> Become a provider
          </button>
        </div>
      </header>

      <PlatformPulseSection />

      {/* Search + type chips */}
      <div className="frame flex flex-wrap items-center gap-3 p-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            className="v-input w-full pl-9"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title, tag, or summary"
          />
        </div>
        <div className="flex flex-wrap gap-1">
          <TypeChip label="All" active={!selectedType} onClick={() => setSelectedType(null)} />
          {typeFilters.map((t) => (
            <TypeChip
              key={t.slug}
              label={`${TYPE_LABEL[t.slug] ?? t.slug} · ${t.count}`}
              active={selectedType === t.slug}
              onClick={() => setSelectedType(selectedType === t.slug ? null : t.slug)}
            />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[200px_1fr]">
        {/* Category sidebar */}
        <aside className="frame h-fit p-3">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
            Categories
          </div>
          <ul className="space-y-1">
            <li>
              <CategoryButton
                label="All categories"
                active={!selectedCategory}
                onClick={() => setSelectedCategory(null)}
              />
            </li>
            {categoryFilters.map((c) => (
              <li key={c.slug}>
                <CategoryButton
                  label={CATEGORY_LABEL[c.slug] ?? c.slug}
                  count={c.count}
                  active={selectedCategory === c.slug}
                  onClick={() => setSelectedCategory(selectedCategory === c.slug ? null : c.slug)}
                />
              </li>
            ))}
          </ul>
        </aside>

        <div className="space-y-6">
          {/* Featured / verified-source strip - only when no filters active */}
          {!selectedType && !selectedCategory && !query && (
            <>
              {featuredQ.data?.featured?.length ? (
                <section>
                  <SectionHeader icon={<Star className="h-4 w-4 text-brass-2" />} title="Featured" />
                  <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                    {featuredQ.data.featured.map((card) => (
                      <ListingCardView key={card.id} card={card} onClick={() => setSelected(card)} />
                    ))}
                  </div>
                </section>
              ) : null}

              {featuredQ.data?.trending?.length ? (
                <section>
                  <SectionHeader
                    icon={<CheckCircle2 className="h-4 w-4 text-electric" />}
                    title="Source verified"
                  />
                  <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {featuredQ.data.trending.map((card) => (
                      <ListingCardView key={card.id} card={card} onClick={() => setSelected(card)} />
                    ))}
                  </div>
                </section>
              ) : null}

              {featuredQ.data?.new?.length ? (
                <section>
                  <SectionHeader icon={<Flame className="h-4 w-4 text-crimson" />} title="New" />
                  <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {featuredQ.data.new.map((card) => (
                      <ListingCardView key={card.id} card={card} onClick={() => setSelected(card)} />
                    ))}
                  </div>
                </section>
              ) : null}
            </>
          )}

          {/* Filtered grid — when any filter is active */}
          {(selectedType || selectedCategory || query) && (
            <section>
              <SectionHeader
                icon={<Tag className="h-4 w-4 text-brass-2" />}
                title={`Results (${filteredAll.length})`}
              />
              {filteredAll.length === 0 ? (
                <div className="frame mt-3 flex flex-col items-center gap-2 py-12 text-center text-sm text-bone-2">
                  <Store className="h-8 w-8 text-brass-2" />
                  No listings match your filters.
                </div>
              ) : (
                <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {filteredAll.map((card) => (
                    <ListingCardView key={card.id} card={card} onClick={() => setSelected(card)} />
                  ))}
                </div>
              )}
            </section>
          )}

          {featuredQ.isError && (
            <div className="frame flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
              <AlertCircle className="mt-0.5 h-4 w-4" />
              <div>
                <div className="font-semibold">Failed to load marketplace</div>
                <div className="mt-1 text-xs opacity-80">
                  {(featuredQ.error as Error)?.message ?? "Unknown error"}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Detail drawer */}
      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink/80 backdrop-blur-sm md:items-center"
          onClick={() => setSelected(null)}
        >
          <div
            className="frame w-full max-w-2xl space-y-4 p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
                  {TYPE_LABEL[selected.listing_type] ?? selected.listing_type}
                  {selected.category ? ` · ${CATEGORY_LABEL[selected.category] ?? selected.category}` : ""}
                </div>
                <h3 className="mt-0.5 truncate text-xl font-semibold">{selected.title}</h3>
                {selected.summary && (
                  <p className="mt-1 text-sm text-bone-2">{selected.summary}</p>
                )}
              </div>
              <button className="text-muted hover:text-bone" onClick={() => setSelected(null)}>
                <X className="h-4 w-4" />
              </button>
            </header>

            {/* Pre-flight intelligence */}
            <section className="rounded-md border border-rule/70 bg-ink-2 p-3">
              <div className="mb-2 flex items-center gap-2">
                <Zap className="h-3.5 w-3.5 text-brass-2" />
                <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                  Pre-flight intelligence
                </div>
              </div>
              {preflightQ.isLoading && (
                <div className="font-mono text-[12px] text-muted">predicting…</div>
              )}
              {preflightQ.isError && (
                <div className="font-mono text-[12px] text-muted">
                  Pre-flight unavailable for this external listing. The listing itself is still live and source-linked.
                </div>
              )}
              {preflightQ.data && (
                <div className="grid grid-cols-3 gap-3 font-mono text-[12px]">
                  <PreflightCell
                    label="cost / run"
                    value={`$${preflightQ.data.predicted_cost_per_run_usd.toFixed(4)}`}
                    sub={`±$${(preflightQ.data.confidence_upper_usd - preflightQ.data.predicted_cost_per_run_usd).toFixed(4)}`}
                    tone="ok"
                  />
                  <PreflightCell
                    label="quality"
                    value={
                      preflightQ.data.predicted_quality != null
                        ? `${(preflightQ.data.predicted_quality * 100).toFixed(0)}%`
                        : "—"
                    }
                    sub={preflightQ.data.predicted_quality != null ? "predicted" : "ml warming"}
                    tone={
                      preflightQ.data.predicted_quality != null && preflightQ.data.predicted_quality > 0.8
                        ? "ok"
                        : "warn"
                    }
                  />
                  <PreflightCell
                    label="failure risk"
                    value={
                      preflightQ.data.failure_risk != null
                        ? `${(preflightQ.data.failure_risk * 100).toFixed(0)}%`
                        : "—"
                    }
                    sub={preflightQ.data.failure_risk != null ? "before run" : "ml warming"}
                    tone={
                      preflightQ.data.failure_risk != null && preflightQ.data.failure_risk < 0.2
                        ? "ok"
                        : "warn"
                    }
                  />
                </div>
              )}
              {preflightQ.data?.alternative_providers?.length ? (
                <div className="mt-3 flex flex-wrap gap-1.5 font-mono text-[10px]">
                  {preflightQ.data.alternative_providers.map((alt) => (
                    <span key={alt.provider} className="v-chip">
                      via {alt.provider} → ${parseFloat(alt.cost).toFixed(4)}
                      {alt.savings_percent > 0 && (
                        <span className="text-moss"> · save {alt.savings_percent.toFixed(0)}%</span>
                      )}
                    </span>
                  ))}
                </div>
              ) : null}
            </section>

            <RunStatePanel
              eyebrow="Tool acquisition flow"
              title="Verify, acquire, then configure"
              status={checkoutMut.isPending ? "running" : checkoutMut.isError ? "failed" : preflightQ.data ? "succeeded" : preflightQ.isLoading ? "running" : preflightQ.isError ? "unavailable" : "idle"}
              summary="Marketplace detail keeps source, price, pre-flight, and acquisition proof on this page before sending the buyer elsewhere."
              steps={[
                { label: "Source and license visible", status: selected.source_url || selected.use_url ? "succeeded" : "unavailable", detail: selected.source_verified ? "verified" : "pending" },
                { label: "Pre-flight estimate", status: preflightQ.isLoading ? "running" : preflightQ.data ? "succeeded" : preflightQ.isError ? "unavailable" : "idle", detail: "/api/v1/marketplace/listings/:id/preflight" },
                { label: selected.price_cents > 0 ? "Checkout" : "Open product", status: checkoutMut.isPending ? "running" : checkoutMut.isError ? "failed" : "idle", detail: selected.price_cents > 0 ? "Stripe checkout" : "external source" },
              ]}
              metrics={[
                { label: "price", value: selected.price_cents > 0 ? fmtCents(selected.price_cents) : "Free" },
                { label: "quality", value: preflightQ.data?.predicted_quality != null ? `${(preflightQ.data.predicted_quality * 100).toFixed(0)}%` : "not returned" },
                { label: "risk", value: preflightQ.data?.failure_risk != null ? `${(preflightQ.data.failure_risk * 100).toFixed(0)}%` : "not returned" },
                { label: "type", value: selected.listing_type },
              ]}
              error={checkoutMut.error}
              actions={[
                ...(selected.source_url || selected.use_url ? [{ label: "View source", href: selected.source_url ?? selected.use_url ?? "#" }] : []),
                selected.price_cents > 0
                  ? { label: checkoutMut.isPending ? "Opening checkout" : "Purchase", onClick: () => checkoutMut.mutate(selected.id), disabled: checkoutMut.isPending, primary: true }
                  : { label: "Open product", href: selected.use_url ?? selected.source_url ?? "#", disabled: !selected.use_url && !selected.source_url, primary: true },
                { label: "View billing", href: "#/billing" },
              ]}
            />

            <ProofStrip
              items={[
                { label: "listing", value: selected.id },
                { label: "source", value: selected.source_verified ? "verified" : "pending" },
                { label: "preflight", value: preflightQ.data ? "returned" : preflightQ.isError ? "unavailable" : "loading" },
                { label: "orders", value: "/api/v1/marketplace/orders/me" },
              ]}
            />

            {/* Compliance badges */}
            {(selected.source_verified || selected.compliance_badges?.length) ? (
              <div className="flex flex-wrap gap-1.5">
                {selected.source_verified && (
                  <span className="v-chip v-chip-ok font-mono text-[10px]" title={selected.verification_note ?? undefined}>
                    <CheckCircle2 className="h-3 w-3" />
                    Source verified
                  </span>
                )}
                {selected.compliance_badges.map((b) => (
                  <span key={b} className="v-chip v-chip-brass font-mono text-[10px]">
                    <ShieldCheck className="h-3 w-3" />
                    {b}
                  </span>
                ))}
              </div>
            ) : null}

            {/* Tags */}
            {selected.tags?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {selected.tags.map((t) => (
                  <span key={t} className="v-chip font-mono text-[10px]">
                    #{t}
                  </span>
                ))}
              </div>
            ) : null}

            {selected.usage && (
              <div className="rounded-md border border-rule/70 bg-ink-1/60 p-3">
                <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                  Usage
                </div>
                <code className="font-mono text-[12px] text-bone">{selected.usage}</code>
              </div>
            )}

            {/* Facts */}
            <div className="grid grid-cols-3 gap-3 border-t border-rule/50 pt-3 text-center font-mono text-[11px] text-muted">
              <div>
                <div className="truncate text-bone">{selected.provider ?? "External"}</div>
                provider
              </div>
              <div>
                <div className={selected.source_verified ? "text-moss" : "text-brass-2"}>
                  {selected.source_verified ? "verified" : "pending"}
                </div>
                source
              </div>
              <div>
                <div className="text-bone">
                  {selected.price_cents > 0 ? fmtCents(selected.price_cents) : "Free"}
                </div>
                price
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center justify-end gap-2 border-t border-rule/50 pt-3">
              {(selected.source_url || selected.use_url) && (
                <a
                  className="v-btn-ghost"
                  href={selected.source_url ?? selected.use_url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                >
                  View source
                </a>
              )}
              {selected.price_cents > 0 ? (
                <button
                  className="v-btn-primary"
                  disabled={checkoutMut.isPending}
                  onClick={() => checkoutMut.mutate(selected.id)}
                >
                  {checkoutMut.isPending ? "Redirecting..." : "Purchase"}
                </button>
              ) : selected.use_url || selected.source_url ? (
                <a
                  className="v-btn-primary"
                  href={selected.use_url ?? selected.source_url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Download className="h-4 w-4" />
                  Open product
                </a>
              ) : selected.listing_type === "pipeline" || selected.listing_type === "agent" ? (
                <button className="v-btn-ghost cursor-not-allowed opacity-70" disabled title="No live install endpoint exists for this listing yet.">
                  Install unavailable
                </button>
              ) : (
                <button className="v-btn-ghost cursor-not-allowed opacity-70" disabled title="This listing has no live source URL yet.">
                  Source unavailable
                </button>
              )}
            </div>

            {checkoutMut.isError && (
              <div className="text-[12px] text-crimson">{apiErrorMessage(checkoutMut.error)}</div>
            )}
          </div>
        </div>
      )}

      {showOrders && <OrdersModal ordersQ={ordersQ} onClose={() => setShowOrders(false)} />}

      {showProvider && (
        <ProviderModal
          displayName={providerName}
          onDisplayName={setProviderName}
          pending={providerMut.isPending}
          error={providerMut.error}
          onClose={() => setShowProvider(false)}
          onSubmit={() => providerName.trim() && providerMut.mutate(providerName)}
        />
      )}
    </div>
  );
}

function OrdersModal({
  ordersQ,
  onClose,
}: {
  ordersQ: ReturnType<typeof useQuery<MarketplaceOrder[]>>;
  onClose: () => void;
}) {
  const orders = ordersQ.data ?? [];
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/80 p-4 backdrop-blur-sm md:items-center">
      <div className="frame w-full max-w-2xl p-5">
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-muted">Marketplace orders</div>
            <h3 className="mt-0.5 text-xl font-semibold text-bone">My purchases</h3>
          </div>
          <button className="text-muted hover:text-bone" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </header>
        {ordersQ.isLoading && <div className="py-8 text-center font-mono text-[12px] text-muted">loading orders...</div>}
        {ordersQ.isError && <div className="text-[12px] text-crimson">{apiErrorMessage(ordersQ.error)}</div>}
        {!ordersQ.isLoading && !ordersQ.isError && orders.length === 0 && (
          <div className="rounded-md border border-dashed border-rule bg-ink-1/50 p-6 text-center text-sm text-muted">
            No marketplace purchases yet.
          </div>
        )}
        {orders.length > 0 && (
          <div className="max-h-[460px] overflow-auto">
            <table className="w-full text-[12px]">
              <thead className="border-b border-rule text-eyebrow">
                <tr>
                  <th className="py-2 text-left">Order</th>
                  <th className="py-2 text-left">Items</th>
                  <th className="py-2 text-left">Status</th>
                  <th className="py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id} className="border-b border-rule/50">
                    <td className="py-2 font-mono text-bone">{order.id.slice(0, 8)}</td>
                    <td className="py-2 text-bone-2">
                      {order.items.map((item) => item.listing_title ?? item.listing_id).join(", ") || "No items"}
                    </td>
                    <td className="py-2">
                      <span className="v-chip">{order.status}</span>
                    </td>
                    <td className="py-2 text-right font-mono text-bone">{fmtCents(order.total_cents, order.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function ProviderModal({
  displayName,
  onDisplayName,
  pending,
  error,
  onClose,
  onSubmit,
}: {
  displayName: string;
  onDisplayName: (value: string) => void;
  pending: boolean;
  error: unknown;
  onClose: () => void;
  onSubmit: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/80 p-4 backdrop-blur-sm md:items-center">
      <div className="frame w-full max-w-lg p-5">
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-muted">Vendor onboarding</div>
            <h3 className="mt-0.5 text-xl font-semibold text-bone">Become a provider</h3>
            <p className="mt-1 text-sm text-bone-2">
              Creates a vendor profile and starts Stripe Connect onboarding when your marketplace plan is eligible.
            </p>
          </div>
          <button className="text-muted hover:text-bone" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </header>
        <label className="block">
          <div className="v-label">Provider display name</div>
          <input
            className="v-input"
            value={displayName}
            onChange={(event) => onDisplayName(event.target.value)}
            placeholder="Veklom Labs"
            autoFocus
          />
        </label>
        <div className="mt-3 rounded-md border border-rule bg-ink-1/60 p-3 text-[12px] text-muted">
          Active paid vendor access is required unless the account is a marketplace admin. If access is not active, the
          backend will return the exact reason and no fake vendor state is created.
        </div>
        {Boolean(error) && <div className="mt-3 text-[12px] text-crimson">{apiErrorMessage(error)}</div>}
        <div className="mt-4 flex justify-end gap-2">
          <button className="v-btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="v-btn-primary" disabled={!displayName.trim() || pending} onClick={onSubmit}>
            {pending ? "Opening Stripe..." : "Start onboarding"}
          </button>
        </div>
      </div>
    </div>
  );
}

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2">
      {icon}
      <h2 className="text-sm font-semibold tracking-tight text-bone">{title}</h2>
    </div>
  );
}

function TypeChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "v-chip font-mono text-[11px] transition",
        active ? "v-chip-brass" : "hover:bg-ink-2",
      )}
    >
      {label}
    </button>
  );
}

function CategoryButton({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-[12px] transition",
        active ? "bg-brass/10 text-brass-2" : "text-bone-2 hover:bg-ink-2",
      )}
    >
      <span>{label}</span>
      {count != null && <span className="font-mono text-[10px] text-muted">{count}</span>}
    </button>
  );
}

function ListingCardView({ card, onClick }: { card: ListingCard; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="frame group flex flex-col gap-2 p-4 text-left transition hover:border-brass/40"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
            <Sparkles className="h-3 w-3 text-brass-2" />
            {TYPE_LABEL[card.listing_type] ?? card.listing_type}
            {card.category ? ` · ${CATEGORY_LABEL[card.category] ?? card.category}` : ""}
          </div>
          <h3 className="mt-1 truncate text-[14px] font-semibold text-bone">{card.title}</h3>
          {card.summary && (
            <p className="mt-1 line-clamp-2 text-[12px] text-bone-2">{card.summary}</p>
          )}
        </div>
        {card.is_featured && <Star className="h-3.5 w-3.5 shrink-0 text-brass-2" />}
      </div>

      {card.compliance_badges?.length ? (
        <div className="flex flex-wrap gap-1">
          {card.compliance_badges.slice(0, 3).map((b) => (
            <span key={b} className="v-chip v-chip-brass font-mono text-[9px]">
              {b}
            </span>
          ))}
        </div>
      ) : null}

      <div className="flex items-center justify-between border-t border-rule/40 pt-2 font-mono text-[10px] text-muted">
        <div className="flex items-center gap-2">
          <span className={card.source_verified ? "text-moss" : "text-brass-2"}>
            <CheckCircle2 className="mr-0.5 inline h-3 w-3" />
            {card.source_verified ? "source verified" : "source pending"}
          </span>
          {card.provider && <span>{card.provider}</span>}
        </div>
        <div>
          {card.predicted_cost_per_run_usd != null ? (
            <span className="text-bone">
              ${card.predicted_cost_per_run_usd.toFixed(4)}
              <span className="text-muted"> / run</span>
            </span>
          ) : card.price_cents > 0 ? (
            <span className="text-bone">{fmtCents(card.price_cents)}</span>
          ) : (
            <span className="text-moss">Free</span>
          )}
        </div>
      </div>
    </button>
  );
}

function PreflightCell({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "ok" | "warn";
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div
        className={cn(
          "mt-0.5 text-base font-semibold",
          tone === "ok" ? "text-moss" : "text-brass-2",
        )}
      >
        {value}
      </div>
      <div className="text-[10px] text-muted">{sub}</div>
    </div>
  );
}
