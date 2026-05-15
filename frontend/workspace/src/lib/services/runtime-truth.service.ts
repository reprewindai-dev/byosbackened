import { api, apiRoot } from "@/lib/api";
import { isRouteUnavailable } from "@/lib/errors";
import { internalService } from "@/lib/services/internal.service";

export type StatusSubscriptionChannel = "email" | "slack";

export async function fetchMonitoringFirstOverview<LegacyOverview, OverviewPayload>({
  convertLegacy,
  hasLive,
}: {
  convertLegacy: (data: LegacyOverview) => OverviewPayload;
  hasLive: (data: OverviewPayload | null | undefined) => boolean;
}): Promise<OverviewPayload> {
  let monitoringOverview: OverviewPayload | null = null;
  try {
    const resp = await api.get<OverviewPayload>("/monitoring/overview");
    monitoringOverview = resp.data;
    if (hasLive(monitoringOverview)) return monitoringOverview;
  } catch (err) {
    if (!isRouteUnavailable(err)) throw err;
  }

  const resp = await api.get<LegacyOverview>("/workspace/overview");
  const legacyOverview = convertLegacy(resp.data);
  if (!monitoringOverview) return legacyOverview;
  return hasLive(legacyOverview) ? legacyOverview : monitoringOverview;
}

export async function fetchStatusRail<T>() {
  return (await apiRoot.get<T>("/status/data")).data;
}

export async function fetchMonitoringHealth<T>() {
  return (await api.get<T>("/monitoring/health")).data;
}

export async function fetchMonitoringAlerts<T>() {
  return (await api.get<T>("/monitoring/alerts")).data;
}

export async function subscribeStatus<T>(channel: StatusSubscriptionChannel, target: string) {
  return (await apiRoot.post<T>("/status/subscribe", { channel, target })).data;
}

export async function fetchOperatorDigest<T>() {
  return (await internalService.operatorDigest()).data as T;
}

export async function fetchOperatorOverview<T>() {
  return (await internalService.operatorOverview()).data as T;
}

export async function fetchUacpSummary<T>() {
  return (await internalService.getUacpSummary()).data as T;
}

export async function fetchUacpMonitoring<T>() {
  return (await internalService.getUacpMonitoring()).data as T;
}

export async function fetchEvaluationSurgeon<T>(limit = 8) {
  return (await internalService.getEvaluationSurgeon({ limit })).data as T;
}

export async function fetchGrowthOpportunities<T>(limit = 8) {
  return (await internalService.getGrowthOpportunities({ limit })).data as T;
}
