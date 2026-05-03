import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ExternalLink,
  Package,
  Search,
  ShieldCheck,
  Sparkles,
  Store,
  Tag,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtCents, cn } from "@/lib/cn";

interface Listing {
  id: string;
  vendor_id: string;
  title: string;
  description: string;
  price_cents: number;
  currency: string;
  status: string;
  created_at: string;
  updated_at?: string;
}

async function fetchListings(): Promise<Listing[]> {
  const resp = await api.get<Listing[]>("/marketplace/listings");
  return resp.data;
}

export function MarketplacePage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["marketplace-listings"],
    queryFn: fetchListings,
  });

  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Listing | null>(null);

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!query.trim()) return data;
    const q = query.toLowerCase();
    return data.filter(
      (l) =>
        l.title.toLowerCase().includes(q) ||
        l.description.toLowerCase().includes(q) ||
        l.vendor_id.toLowerCase().includes(q),
    );
  }, [data, query]);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Marketplace
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Sovereign-ready asset catalog</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Vetted models, pipelines, evals, and prompt packs from governed vendors. Every listing ships with
            provenance, licensing, and deployment manifest.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              live · <span className="font-mono">/api/v1/marketplace/listings</span>
            </span>
            <span className="v-chip v-chip-brass">Stripe Connect payouts</span>
            <span className="v-chip">vendor-vetted</span>
          </div>
        </div>
        <div className="flex gap-2">
          <a href="/vendor" className="v-btn-ghost">
            <Store className="h-4 w-4" /> Vendor dashboard
          </a>
        </div>
      </header>

      <div className="v-card flex items-center gap-3 p-3">
        <Search className="ml-1 h-4 w-4 text-muted" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search listings, vendors, tags…"
          className="w-full bg-transparent text-[14px] outline-none placeholder:text-muted-2"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone"
            aria-label="Clear"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        <span className="v-chip font-mono">
          {isLoading ? "…" : `${filtered.length} / ${data?.length ?? 0}`}
        </span>
      </div>

      {isError && (
        <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load listings</div>
            <div className="mt-1 text-xs opacity-80">
              {(error as Error)?.message ?? "Unknown error"} · the backend may be offline.
            </div>
          </div>
          <button className="v-btn-ghost" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="v-card h-48 animate-pulse bg-ink-2" />
          ))}
        </div>
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <div className="v-card flex flex-col items-center gap-3 px-6 py-16 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brass/10 text-brass-2">
            <Package className="h-6 w-6" />
          </div>
          <div className="text-lg font-semibold">
            {query ? "No listings match" : "Marketplace is empty"}
          </div>
          <p className="max-w-md text-sm text-bone-2">
            {query
              ? "Try a different search term or clear the filter."
              : "No approved listings yet. When vendors publish, listings will appear here."}
          </p>
        </div>
      )}

      {!isLoading && !isError && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((l) => (
            <button
              key={l.id}
              onClick={() => setSelected(l)}
              className="v-card flex flex-col items-start gap-3 p-4 text-left transition hover:border-brass/40 hover:bg-ink-2/60"
            >
              <div className="flex w-full items-start justify-between gap-2">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brass/10 text-brass-2">
                  <Package className="h-5 w-5" />
                </div>
                <span
                  className={cn(
                    "v-chip font-mono text-[10px]",
                    l.status === "published" ? "v-chip-ok" : "v-chip-warn",
                  )}
                >
                  {l.status}
                </span>
              </div>
              <div className="w-full">
                <div className="line-clamp-2 text-[15px] font-semibold tracking-tight text-bone">
                  {l.title}
                </div>
                <div className="mt-1 line-clamp-2 text-[12px] text-bone-2">{l.description}</div>
              </div>
              <div className="mt-auto flex w-full items-end justify-between">
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
                    vendor
                  </div>
                  <div className="font-mono text-[11px] text-bone-2">
                    {l.vendor_id.slice(0, 8)}…
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
                    {l.currency.toUpperCase()}
                  </div>
                  <div className="font-mono text-lg font-semibold text-brass-2">
                    {fmtCents(l.price_cents, l.currency)}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <ListingDrawer listing={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function ListingDrawer({ listing, onClose }: { listing: Listing; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true">
      <button
        className="flex-1 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Close"
      />
      <aside className="flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-rule bg-ink-1">
        <header className="sticky top-0 flex items-center justify-between border-b border-rule bg-ink-1/90 px-5 py-3 backdrop-blur">
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
            Listing detail
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="space-y-5 px-5 py-5">
          <div className="flex items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-brass/10 text-brass-2">
              <Package className="h-6 w-6" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold tracking-tight text-bone">{listing.title}</h2>
              <div className="mt-1 flex flex-wrap gap-2">
                <span className="v-chip font-mono text-[10px]">
                  <Tag className="h-3 w-3" /> {listing.id.slice(0, 10)}…
                </span>
                <span
                  className={cn(
                    "v-chip font-mono text-[10px]",
                    listing.status === "published" ? "v-chip-ok" : "v-chip-warn",
                  )}
                >
                  {listing.status}
                </span>
              </div>
            </div>
          </div>

          <div className="v-card p-4">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">Price</div>
            <div className="font-mono text-3xl font-semibold text-brass-2">
              {fmtCents(listing.price_cents, listing.currency)}
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted">
              {listing.currency.toUpperCase()} · one-time via Stripe Connect
            </div>
          </div>

          <section>
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Description
            </div>
            <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-bone-2">
              {listing.description || "No description provided."}
            </p>
          </section>

          <section>
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Vendor
            </div>
            <div className="v-card flex items-center gap-3 p-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-electric/10 text-electric">
                <Store className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <div className="font-mono text-[11px] text-bone">{listing.vendor_id}</div>
                <div className="font-mono text-[10px] text-muted">verified vendor</div>
              </div>
            </div>
          </section>

          <section>
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Governance
            </div>
            <ul className="space-y-1.5 font-mono text-[11px]">
              {[
                { icon: ShieldCheck, text: "Tenant-isolated deployment" },
                { icon: ShieldCheck, text: "License fingerprinted at install" },
                { icon: Sparkles, text: "Runs inside your sovereign control plane" },
                { icon: ShieldCheck, text: "Vendor liability via Marketplace Vendor Agreement" },
              ].map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-2 text-bone-2">
                  <Icon className="h-3 w-3 text-moss" />
                  {text}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Install
            </div>
            <div className="v-card border-brass/30 bg-brass/5 p-4 text-[12px] text-bone-2">
              <div className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-brass-2">
                <ExternalLink className="h-3 w-3" /> Stripe Connect checkout
              </div>
              Purchase kicks off a governed install — Stripe Checkout → order webhook → tenant-scoped install →
              workspace wallet debit. The buyer flow opens shortly; vendor payouts route via Stripe Connect with
              platform fee retention.
            </div>
            <button
              className="v-btn-primary mt-3 w-full"
              onClick={() => alert("Purchase flow ships in the next commit wave. Endpoint: POST /api/v1/marketplace/payments/create-checkout")}
            >
              <Sparkles className="h-4 w-4" /> Purchase &amp; install
            </button>
            <div className="mt-2 text-center font-mono text-[10px] text-muted">
              created {new Date(listing.created_at).toLocaleString()}
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
