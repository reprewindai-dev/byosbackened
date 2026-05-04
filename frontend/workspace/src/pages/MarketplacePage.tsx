import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  TrendingUp,
  X,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtCents, cn } from "@/lib/cn";

interface ListingCard {
  id: string;
  slug?: string | null;
  title: string;
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
    .sort((a, b) => b.install_count - a.install_count || b.rating_avg - a.rating_avg)
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
  const rating = Number(row.rating_avg ?? row.rating ?? 0);
  const installs = Number(row.install_count ?? row.installs ?? 0);

  return {
    id: String(row.id ?? row.slug ?? row.title ?? ""),
    slug: row.slug ? String(row.slug) : String(row.id ?? ""),
    title: String(row.title ?? row.name ?? ""),
    summary: row.summary ? String(row.summary) : String(row.description ?? row.positioning ?? ""),
    listing_type: String(row.listing_type ?? inferredType),
    category,
    tags,
    compliance_badges: badges,
    price_cents: Number(row.price_cents ?? 0),
    currency: String(row.currency ?? "usd"),
    predicted_cost_per_run_usd: row.predicted_cost_per_run_usd != null ? Number(row.predicted_cost_per_run_usd) : null,
    rating_avg: rating,
    rating_count: Number(row.rating_count ?? (rating ? 1 : 0)),
    install_count: installs,
    is_featured: Boolean(row.is_featured ?? row.featured),
    source_url: row.source_url ? String(row.source_url) : null,
    use_url: row.use_url ? String(row.use_url) : row.source_url ? String(row.source_url) : null,
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
    types: [
      { slug: "connector", count: categories.reduce((sum, row) => sum + row.count, 0) },
      { slug: "pipeline", count: 0 },
      { slug: "tool", count: 0 },
    ],
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

export function MarketplacePage() {
  const qc = useQueryClient();
  const { slug } = useParams();
  const [query, setQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selected, setSelected] = useState<ListingCard | null>(null);

  const featuredQ = useQuery({ queryKey: ["mkt-featured"], queryFn: fetchFeatured });
  const categoriesQ = useQuery({ queryKey: ["mkt-categories"], queryFn: fetchCategories });
  const preflightQ = useQuery({
    queryKey: ["mkt-preflight", selected?.id],
    queryFn: () => fetchPreflight(selected!.id),
    enabled: !!selected,
  });

  const installMut = useMutation({
    mutationFn: async (id: string) => {
      const r = await api.post<{ pipeline_id: string; pipeline_slug: string; install_count: number }>(
        `/marketplace/listings/${id}/install`,
        {},
      );
      return r.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mkt-featured"] });
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
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Marketplace
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Self-organizing AI marketplace</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Every listing is auto-classified, auto-validated, and ships with pre-flight cost,
            quality, and failure-risk predictions for your workspace's data context. One-click
            install turns any pipeline listing into a live, audited workflow.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" /> live ·{" "}
              <span className="font-mono">/api/v1/marketplace</span>
            </span>
            <span className="v-chip v-chip-brass">{allCards.length} listings</span>
          </div>
        </div>
      </header>

      {/* Search + type chips */}
      <div className="v-card flex flex-wrap items-center gap-3 p-3">
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
          {categoriesQ.data?.types.map((t) => (
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
        <aside className="v-card h-fit p-3">
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
            {categoriesQ.data?.categories.map((c) => (
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
          {/* Featured / Trending strip — only when no filters active */}
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
                    icon={<TrendingUp className="h-4 w-4 text-electric" />}
                    title="Trending"
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
                <div className="v-card mt-3 flex flex-col items-center gap-2 py-12 text-center text-sm text-bone-2">
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
            <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
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
            className="v-card w-full max-w-2xl space-y-4 p-5"
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

            {/* Compliance badges */}
            {selected.compliance_badges?.length ? (
              <div className="flex flex-wrap gap-1.5">
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

            {/* Stats */}
            <div className="grid grid-cols-3 gap-3 border-t border-rule/50 pt-3 text-center font-mono text-[11px] text-muted">
              <div>
                <div className="text-bone">{selected.install_count}</div>
                installs
              </div>
              <div>
                <div className="text-bone">
                  {selected.rating_avg ? selected.rating_avg.toFixed(1) : "—"}
                </div>
                rating ({selected.rating_count})
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
              {selected.price_cents > 0 ? (
                <button
                  className="v-btn-primary"
                  disabled={checkoutMut.isPending}
                  onClick={() => checkoutMut.mutate(selected.id)}
                >
                  {checkoutMut.isPending ? "Redirecting…" : "Purchase"}
                </button>
              ) : selected.listing_type !== "pipeline" && selected.listing_type !== "agent" ? (
                <a
                  className="v-btn-primary"
                  href={selected.use_url ?? selected.source_url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Download className="h-4 w-4" />
                  Open product
                </a>
              ) : (
                <button
                  className="v-btn-primary"
                  disabled={installMut.isPending}
                  onClick={() => installMut.mutate(selected.id)}
                >
                  <Download className="h-4 w-4" />
                  {installMut.isPending
                    ? "Installing…"
                    : installMut.isSuccess
                    ? "Installed"
                    : "One-click install"}
                </button>
              )}
            </div>

            {installMut.isSuccess && (
              <div className="flex items-center gap-2 rounded-md border border-moss/40 bg-moss/5 px-3 py-2 text-[12px] text-moss">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Installed as pipeline{" "}
                <span className="font-mono">{installMut.data?.pipeline_slug}</span>
              </div>
            )}
            {installMut.isError && (
              <div className="text-[12px] text-crimson">
                {(installMut.error as { response?: { data?: { detail?: string } } })?.response?.data
                  ?.detail ?? (installMut.error as Error)?.message}
              </div>
            )}
            {checkoutMut.isError && (
              <div className="text-[12px] text-crimson">
                {(checkoutMut.error as { response?: { data?: { detail?: string } } })?.response
                  ?.data?.detail ?? (checkoutMut.error as Error)?.message}
              </div>
            )}
          </div>
        </div>
      )}
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
      className="v-card group flex flex-col gap-2 p-4 text-left transition hover:border-brass/40"
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
          <span>
            <Download className="mr-0.5 inline h-3 w-3" />
            {card.install_count}
          </span>
          {card.rating_count > 0 && (
            <span>
              <Star className="mr-0.5 inline h-3 w-3 text-brass-2" />
              {card.rating_avg.toFixed(1)}
            </span>
          )}
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
