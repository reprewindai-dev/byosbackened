import { Box, ExternalLink, Power, PowerOff, RefreshCw } from "lucide-react";
import { usePlugins, useTogglePlugin } from "@/hooks/usePlugins";
import { cn } from "@/lib/cn";

export function PluginsPage() {
  const pluginsQ = usePlugins();
  const toggle = useTogglePlugin();
  const plugins = pluginsQ.data ?? [];
  const enabledCount = plugins.filter((plugin) => plugin.enabled).length;

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Extensions</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Plugin Registry</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Workspace plugin control wired to the backend plugin registry.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="v-chip v-chip-brass">{plugins.length} plugins</span>
          <span className="v-chip v-chip-ok">{enabledCount} enabled</span>
        </div>
      </header>

      {pluginsQ.isLoading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="frame h-40 animate-pulse bg-white/[0.02]" />
          ))}
        </div>
      ) : pluginsQ.isError ? (
        <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">
          Could not load plugins. Backend route is /plugins.
        </div>
      ) : plugins.length === 0 ? (
        <div className="frame border-dashed p-8 text-center text-sm text-muted">No plugins returned by backend registry.</div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {plugins.map((plugin) => {
            const slug = plugin.slug || plugin.id;
            return (
              <article key={plugin.id} className="frame p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="rounded-md border border-brass/25 bg-brass/10 p-2 text-brass">
                      <Box className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="truncate font-semibold text-bone">{plugin.name}</h2>
                      <div className="mt-1 font-mono text-[11px] text-muted">v{plugin.version} - {plugin.author}</div>
                    </div>
                  </div>
                  <span className={cn("v-chip", plugin.enabled ? "v-chip-ok" : "border-white/10 bg-white/[0.03] text-muted")}>
                    {plugin.enabled ? "enabled" : "disabled"}
                  </span>
                </div>

                <p className="mt-4 min-h-[54px] text-sm leading-6 text-muted">{plugin.description}</p>

                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="v-chip v-chip-brass">{plugin.category}</span>
                  {plugin.installed ? <span className="v-chip v-chip-ok">installed</span> : <span className="v-chip">available</span>}
                </div>

                <div className="mt-5 flex items-center justify-between gap-2 border-t border-rule pt-4">
                  <a className="btn-secondary" href={`/api/v1/plugins/${encodeURIComponent(slug)}/docs`} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-4 w-4" /> Docs
                  </a>
                  <button
                    type="button"
                    className={plugin.enabled ? "btn-secondary" : "btn-primary"}
                    disabled={toggle.isPending}
                    onClick={() => toggle.mutate({ slug, enabled: !plugin.enabled })}
                  >
                    {toggle.isPending ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : plugin.enabled ? (
                      <PowerOff className="h-4 w-4" />
                    ) : (
                      <Power className="h-4 w-4" />
                    )}
                    {plugin.enabled ? "Disable" : "Enable"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
