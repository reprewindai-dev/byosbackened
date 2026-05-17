export function responseStatus(error: unknown): number | undefined {
  return (error as { response?: { status?: number } })?.response?.status;
}

export function responseDetail(error: unknown): string {
  const code = (error as { code?: string })?.code;
  const message = (error as Error)?.message;
  const timeout = (error as { config?: { timeout?: number } })?.config?.timeout;
  const data = (error as { response?: { data?: unknown } })?.response?.data;
  if (typeof data === "string") return data;
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  if (code === "ECONNABORTED" || /timeout/i.test(message ?? "")) {
    const seconds = timeout ? Math.round(timeout / 1000) : undefined;
    return seconds
      ? `Request timed out after ${seconds}s waiting for the live backend/model response.`
      : "Request timed out waiting for the live backend/model response.";
  }
  if (code === "ERR_NETWORK" || /network error/i.test(message ?? "")) {
    return "Network transport failed before the backend returned a response. Check API reachability, CORS, or a browser-side timeout.";
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
