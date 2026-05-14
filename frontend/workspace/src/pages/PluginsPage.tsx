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

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Extensions</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Plugin Registry</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Install, configure, and manage workspace plugins. Integrations, model adapters, compliance tools, and monitoring extensions.
        </p>
      </header>

      {/* Installed */}
      <section className="mb-8">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <Settings2 className="h-4 w-4 text-brass" /> Installed ({installed.length})
        </h2>
        {pluginsQ.isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="frame h-32 animate-pulse bg-white/[0.02]" />)}</div>
        ) : pluginsQ.isError ? (
          <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">Could not load plugins — /plugins may not be deployed yet.</div>
        ) : installed.length === 0 ? (
          <div className="frame border-dashed p-6 text-center text-sm text-muted">No plugins installed. Browse available plugins below.</div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {installed.map((plugin) => (
              <div key={plugin.id} className="frame p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-bone">{plugin.name}</div>
                    <div className="mt-0.5 text-xs text-muted">v{plugin.version} · {plugin.author}</div>
                  </div>
                  <span className={cn("v-chip", plugin.category === "compliance" && "v-chip-ok", plugin.category === "monitoring" && "v-chip-brass")}>{plugin.category}</span>
                </div>
                <p className="mt