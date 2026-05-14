/**
 * ServicesPage — BYOS internal service topology dashboard.
 *
 * Shows all internal services (AI providers, workspace gateway, billing,
 * security, monitoring) and how they wire together.
 */
import { useServiceRegistry, useServiceTopology } from "@/hooks/useServiceGateway";

const statusColors: Record<string, string> = {
  healthy: "text-emerald-400",
  degraded: "text-amber-400",
  unhealthy: "text-red-400",
  unknown: "text-zinc-400",
};

const statusDots: Record<string, string> = {
  healthy: "bg-emerald-400",
  degraded: "bg-amber-400",
  unhealthy: "bg-red-400",
  unknown: "bg-zinc-500",
};

const typeLabels: Record<string, string> = {
  ai_provider: "AI Provider",
  core: "Core",
  integration: "Integration",
  monitoring: "Monitoring",
  billing: "Billing",
};

const typeBadgeColors: Record<string, string> = {
  ai_provider: "bg-purple-500/20 text-purple-300",
  core: "bg-cyan-500/20 text-cyan-300",
  integration: "bg-blue-500/20 text-blue-300",
  monitoring: "bg-amber-500/20 text-amber-300",
  billing: "bg-emerald-500/20 text-emerald-300",
};

const layerLabels: Record<string, string> = {
  ai_providers: "AI Providers",
  core: "Core Services",
  integrations: "Integrations",
  monitoring: "Monitoring",
  billing: "Billing",
};

export default function ServicesPage() {
  const { data: registry, isLoading: regLoading } = useServiceRegistry();
  const { data: topology, isLoading: topoLoading } = useServiceTopology();

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Internal Services</h1>
        <p className="mt-1 text-sm text-zinc-400">
          BYOS platform services — AI providers, routing, security, billing, and monitoring.
        </p>
      </header>

      {/* Topology wiring */}
      {!topoLoading && topology && (
        <section className="rounded-xl border border-zinc-700/60 bg-zinc-800/50 p-6">
          <h2 className="text-lg font-medium text-white mb-4">Internal Wiring</h2>
          <div className="space-y-3">
            {topology.wiring.map((edge, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg bg-zinc-900/60 px-4 py-3 text-sm"
              >
                <span className="font-mono text-cyan-300">{edge.from}</span>
                <span className="text-zinc-500">&rarr;</span>
                <span className="font-mono text-emerald-300">{edge.to}</span>
                <span className="ml-auto text-xs text-zinc-500">{edge.protocol}</span>
                <span className="text-xs text-zinc-400 max-w-[350px] truncate">
                  {edge.description}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Service registry table */}
      <section className="rounded-xl border border-zinc-700/60 bg-zinc-800/50 p-6">
        <h2 className="text-lg font-medium text-white mb-4">
          Platform Services
          {registry && (
            <span className="ml-2 text-sm text-zinc-400">({registry.total})</span>
          )}
        </h2>

        {regLoading ? (
          <p className="text-zinc-400 text-sm">Loading services…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-700/60 text-zinc-400">
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Service</th>
                  <th className="pb-3 pr-4">Type</th>
                  <th className="pb-3 pr-4">URL</th>
                  <th className="pb-3 pr-4">Enabled</th>
                </tr>
              </thead>
              <tbody>
                {registry?.services.map((svc) => (
                  <tr
                    key={svc.service_id}
                    className="border-b border-zinc-700/30 hover:bg-zinc-700/20"
                  >
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${statusDots[svc.status] ?? statusDots.unknown}`}
                        />
                        <span className={statusColors[svc.status] ?? statusColors.unknown}>
                          {svc.status}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      <div>
                        <span className="font-medium text-white">{svc.name}</span>
                        <span className="ml-2 text-xs text-zinc-500 font-mono">
                          {svc.service_id}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${typeBadgeColors[svc.service_type] ?? "bg-zinc-600/30 text-zinc-300"}`}
                      >
                        {typeLabels[svc.service_type] ?? svc.service_type}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      {svc.base_url ? (
                        <span className="text-cyan-400 font-mono text-xs">
                          {svc.base_url}
                        </span>
                      ) : (
                        <span className="text-zinc-500 text-xs">&mdash;</span>
                      )}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={svc.enabled ? "text-emerald-400" : "text-zinc-500"}
                      >
                        {svc.enabled ? "Yes" : "No"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Topology layers */}
      {!topoLoading && topology && (
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(topology.layers).map(([layer, services]) => (
            <div
              key={layer}
              className="rounded-xl border border-zinc-700/60 bg-zinc-800/50 p-5"
            >
              <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide mb-3">
                {layerLabels[layer] ?? layer}
              </h3>
              {services.length === 0 ? (
                <p className="text-xs text-zinc-500">No services</p>
              ) : (
                <div className="space-y-2">
                  {services.map((s: { id: string; name: string; status: string; enabled: boolean }) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between rounded bg-zinc-900/50 px-3 py-2 text-xs"
                    >
                      <span className="text-white">{s.name}</span>
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${statusDots[s.status] ?? statusDots.unknown}`}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
