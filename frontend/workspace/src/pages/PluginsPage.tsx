import { useInstallPlugin, usePlugins, useTogglePlugin, useUninstallPlugin, useUpdatePluginConfig } from "@/hooks/usePlugins";
import { cn } from "@/lib/cn";
import { Box, Download, ExternalLink, Settings2, Trash2 } from "lucide-react";
import { useState } from "react";

export function PluginsPage() {
  const pluginsQ = usePlugins();
  const install = useInstallPlugin();
  const uninstall = useUninstallPlugin();
  const toggle = useTogglePlugin();
  const [configuring, setConfiguring] = useState<string | null>(null);
  const [configDraft, setConfigDraft] = useState<Record<string, string>>({});
  const updateConfig = useUpdatePluginConfig();

  const installed = (pluginsQ.data ?? []).filter((p) => p.installed);
  const available = (pluginsQ.data ?? []).filter((p) => !p.installed);

  function catColor(cat: string) {
    if (cat === "compliance") return "bg-moss/15 text-moss";
    if (cat === "monitoring") return "bg-amber/15 text-amber";
    if (cat === "security") return "bg-crimson/15 text-crimson";
    return "bg-electric/15 text-electric";
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <p className="v-section-label">Extensions</p>
        <h1 className="mt-1 text-2xl font-bold text-bone">Plugin Registry</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          Install, configure, and manage workspace plugins. Integrations, model adapters, compliance tools, and monitoring extensions.
        </p>
      </div>

      {/* Installed */}
      <div>
        <p className="v-section-label mb-3 flex items-center gap-2">
          <Settings2 className="h-3.5 w-3.5 text-amber" /> Installed ({installed.length})
        </p>
        {pluginsQ.isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="v-card h-32 animate-pulse" />
            ))}
          </div>
        ) : pluginsQ.isError ? (
          <div className="v-card border-crimson/30 text-sm text-crimson">
            Could not load plugins — /plugins may not be deployed yet.
          </div>
        ) : installed.length === 0 ? (
          <div className="v-card border-dashed text-center text-sm text-muted py-6">
            No plugins installed. Browse available plugins below.
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {installed.map((plugin) => (
              <div key={plugin.id} className="v-card">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-bone">{plugin.name}</div>
                    <div className="mt-0.5 text-[10px] text-muted">
                      v{plugin.version} · {plugin.author}
                    </div>
                  </div>
                  <span className={`rounded px-1.5 py-0.5 text-[8px] font-mono font-semibold ${catColor(plugin.category)}`}>
                    {plugin.category}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted">{plugin.description}</p>
                <div className="mt-3 flex items-center gap-2">
                  <button
                    onClick={() => toggle.mutate({ slug: plugin.slug, enabled: !plugin.enabled })}
                    className={cn(
                      "rounded px-2 py-1 text-xs font-medium",
                      plugin.enabled
                        ? "bg-moss/10 text-moss hover:bg-moss/20"
                        : "bg-white/5 text-muted hover:bg-white/10",
                    )}
                  >
                    {plugin.enabled ? "Enabled" : "Disabled"}
                  </button>
                  <button
                    onClick={() => {
                      setConfiguring(plugin.slug);
                      setConfigDraft(
                        Object.fromEntries(
                          Object.entries(plugin.config_values ?? {}).map(([k, v]) => [k, String(v)]),
                        ),
                      );
                    }}
                    className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone"
                  >
                    <Settings2 className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => uninstall.mutate(plugin.slug)}
                    className="rounded p-1 text-muted hover:bg-crimson/10 hover:text-crimson"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                {configuring === plugin.slug && (
                  <div className="mt-3 border-t border-rule pt-3">
                    {Object.keys(plugin.config_schema ?? {}).length === 0 ? (
                      <div className="text-xs text-muted">No configurable options.</div>
                    ) : (
                      <>
                        {Object.keys(plugin.config_schema ?? {}).map((key) => (
                          <label key={key} className="mb-2 block text-xs">
                            <span className="text-muted">{key}</span>
                            <input
                              className="v-input mt-1 w-full"
                              value={configDraft[key] ?? ""}
                              onChange={(e) => setConfigDraft((d) => ({ ...d, [key]: e.target.value }))}
                            />
                          </label>
                        ))}
                        <button
                          className="v-btn-primary text-xs px-3 py-1 mt-1"
                          onClick={() => {
                            updateConfig.mutate({ slug: plugin.slug, config: configDraft });
                            setConfiguring(null);
                          }}
                        >
                          Save
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Available */}
      <div>
        <p className="v-section-label mb-3 flex items-center gap-2">
          <Box className="h-3.5 w-3.5 text-amber" /> Available ({available.length})
        </p>
        {available.length === 0 ? (
          <div className="v-card border-dashed text-center text-sm text-muted py-6">
            All plugins are installed.
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {available.map((plugin) => (
              <div key={plugin.id} className="v-card">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-bone">{plugin.name}</div>
                    <div className="mt-0.5 text-[10px] text-muted">
                      v{plugin.version} · {plugin.author}
                    </div>
                  </div>
                  <span className={`rounded px-1.5 py-0.5 text-[8px] font-mono font-semibold ${catColor(plugin.category)}`}>
                    {plugin.category}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted">{plugin.description}</p>
                <div className="mt-3 flex items-center gap-2">
                  <button
                    onClick={() => install.mutate(plugin.slug)}
                    className="flex items-center gap-1 rounded bg-amber/15 border border-amber/30 px-2.5 py-1 text-xs font-medium text-amber hover:bg-amber/25"
                  >
                    <Download className="h-3 w-3" /> Install
                  </button>
                  {plugin.marketplace_url && (
                    <a
                      href={plugin.marketplace_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-muted hover:text-bone"
                    >
                      <ExternalLink className="h-3 w-3" /> View
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
