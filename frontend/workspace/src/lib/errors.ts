export function responseStatus(error: unknown): number | undefined {
  return (error as { response?: { status?: number } })?.response?.status;
}

export function responseDetail(error: unknown): string {
  const code = (error as { code?: string })?.code;
  const message = (error as Error)?.message;
  const config = (error as { config?: { timeout?: number; method?: string; url?: string; baseURL?: string } })?.config;
  const timeout = config?.timeout;
  const method = config?.method?.toUpperCase();
  const url = config?.url;
  const route = method && url ? `${method} ${url}` : url;
  const data = (error as { response?: { data?: unknown } })?.response?.data;
  if (typeof data === "string") return data;
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  if (code === "ECONNABORTED" || /timeout/i.test(message ?? "")) {
    const seconds = timeout ? Math.round(timeout / 1000) : undefined;
    return seconds
      ? `${route ? `${route} ` : ""}timed out after ${seconds}s waiting for the live backend/model response.`
      : `${route ? `${route} ` : "Request"} timed out waiting for the live backend/model response.`;
  }
  if (code === "ERR_NETWORK" || /network error/i.test(message ?? "")) {
    const base = config?.baseURL ? ` via ${config.baseURL}` : "";
    return `${route ? `${route} ` : "Request"}could not reach the live API${base}. The browser did not receive a backend response; retry once, then check auth/session and API health.`;
  }
  return message ?? "Request failed";
}

export function isRouteUnavailable(error: unknown): boolean {
  const status = responseStatus(error);
  return status === 404 || status === 405 || status === 501;
}

export function actionUnavailableMessage(error: unknown, label: string): string {
  const status = responseStatus(error);
  if (status === 404 || status === 405 || status === 501) {
    return `${label} is not enabled on the live backend yet.`;
  }
  return responseDetail(error);
}
