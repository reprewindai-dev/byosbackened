export function responseStatus(error: unknown): number | undefined {
  return (error as { response?: { status?: number } })?.response?.status;
}

export function responseDetail(error: unknown): string {
  const data = (error as { response?: { data?: unknown } })?.response?.data;
  if (typeof data === "string") return data;
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return (error as Error)?.message ?? "Request failed";
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
