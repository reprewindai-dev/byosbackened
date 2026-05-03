import { Construction } from "lucide-react";

export function PlaceholderPage({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mx-auto w-full max-w-5xl">
      <header className="mb-6">
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">Workspace</div>
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-2 text-sm text-bone-2">{subtitle}</p>}
      </header>
      <div className="v-card flex flex-col items-center gap-3 px-6 py-16 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brass/10 text-brass-2">
          <Construction className="h-6 w-6" />
        </div>
        <div className="text-lg font-semibold">Screen under construction</div>
        <p className="max-w-md text-sm text-bone-2">
          This surface is specced and mapped to backend endpoints in <span className="font-mono text-brass-2">BACKEND_API_INVENTORY.md</span>. It ships in the next phase of the workspace rebuild.
        </p>
        <div className="mt-2 flex gap-2 font-mono text-[11px]">
          <span className="v-chip">backend · ready</span>
          <span className="v-chip v-chip-warn">frontend · pending</span>
        </div>
      </div>
    </div>
  );
}
