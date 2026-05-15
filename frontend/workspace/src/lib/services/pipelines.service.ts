import { api, noRoute, sseUrl } from "@/lib/api";

export const pipelinesService = {
  // ─── Pipelines ───────────────────────────────────────────
  /** GET /pipelines */
  list: (params?: { page?: number; limit?: number; status?: string }) =>
    api.get("/pipelines", { params }),

  /** POST /pipelines */
  create: (body: Record<string, unknown>) => api.post("/pipelines", body),

  /** GET /pipelines/{pipeline_id} */
  get: (pipeline_id: string) => api.get(`/pipelines/${pipeline_id}`),

  /** PATCH /pipelines/{pipeline_id} */
  update: (pipeline_id: string, body: Record<string, unknown>) =>
    api.patch(`/pipelines/${pipeline_id}`, body),

  /** DELETE /pipelines/{pipeline_id} */
  delete: (pipeline_id: string) => api.delete(`/pipelines/${pipeline_id}`),

  /** POST /pipelines/{pipeline_id}/run */
  run: (pipeline_id: string, body?: Record<string, unknown>) =>
    api.post(`/pipelines/${pipeline_id}/run`, body),

  /** POST /pipelines/{pipeline_id}/execute */
  execute: (pipeline_id: string, body?: Record<string, unknown>) =>
    api.post(`/pipelines/${pipeline_id}/execute`, body),

  /** No route found: POST /pipelines/{pipeline_id}/stop */
  stop: (pipeline_id: string) => noRoute(`/pipelines/${pipeline_id}/stop`),

  /** GET /pipelines/runs/recent */
  recentRuns: (params?: { limit?: number }) => api.get("/pipelines/runs/recent", { params }),

  /** GET /pipelines/{pipeline_id}/runs */
  listRuns: (pipeline_id: string, params?: { page?: number; limit?: number }) =>
    api.get(`/pipelines/${pipeline_id}/runs`, { params }),

  /** GET /pipelines/{pipeline_id}/versions */
  listVersions: (pipeline_id: string) => api.get(`/pipelines/${pipeline_id}/versions`),

  /** POST /pipelines/{pipeline_id}/versions */
  createVersion: (pipeline_id: string, body: Record<string, unknown>) =>
    api.post(`/pipelines/${pipeline_id}/versions`, body),

  /** No route found: GET /pipelines/{pipeline_id}/runs/{run_id} */
  getRun: (pipeline_id: string, run_id: string) =>
    noRoute(`/pipelines/${pipeline_id}/runs/${run_id}`),

  /** No route found: SSE /pipelines/{pipeline_id}/runs/{run_id}/stream */
  runStreamUrl: (pipeline_id: string, run_id: string) =>
    noRoute(`/pipelines/${pipeline_id}/runs/${run_id}/stream`),

  // ─── Deployments ─────────────────────────────────────────
  /** GET /deployments */
  listDeployments: (params?: { page?: number; limit?: number; status?: string }) =>
    api.get("/deployments", { params }),

  /** POST /deployments */
  createDeployment: (body: Record<string, unknown>) =>
    api.post("/deployments", body),

  /** GET /deployments/{deployment_id} */
  getDeployment: (deployment_id: string) =>
    api.get(`/deployments/${deployment_id}`),

  /** PATCH /deployments/{deployment_id} */
  updateDeployment: (deployment_id: string, body: Record<string, unknown>) =>
    api.patch(`/deployments/${deployment_id}`, body),

  /** DELETE /deployments/{deployment_id} */
  deleteDeployment: (deployment_id: string) =>
    api.delete(`/deployments/${deployment_id}`),

  /** POST /deployments/{deployment_id}/promote */
  promoteDeployment: (deployment_id: string, body?: { target_traffic_percent?: number }) =>
    api.post(`/deployments/${deployment_id}/promote`, body),

  /** POST /deployments/{deployment_id}/rollback */
  rollbackDeployment: (deployment_id: string, body?: Record<string, unknown>) =>
    api.post(`/deployments/${deployment_id}/rollback`, body),

  /** POST /deployments/{deployment_id}/test */
  testDeployment: (deployment_id: string, body: Record<string, unknown>) =>
    api.post(`/deployments/${deployment_id}/test`, body),

  /** No route found: POST /deployments/{deployment_id}/scale */
  scaleDeployment: (deployment_id: string, body: { replicas: number }) =>
    noRoute(`/deployments/${deployment_id}/scale`, body),

  /** No route found: POST /deployments/{deployment_id}/restart */
  restartDeployment: (deployment_id: string) =>
    noRoute(`/deployments/${deployment_id}/restart`),

  /** No route found: GET /deployments/{deployment_id}/logs */
  getDeploymentLogs: (deployment_id: string, params?: { from?: string; limit?: number }) =>
    noRoute(`/deployments/${deployment_id}/logs`, params),

  // ─── Jobs ────────────────────────────────────────────────
  /** GET /job */
  listJobs: (params?: { status?: string; page?: number; limit?: number }) =>
    api.get("/job", { params }),

  /** GET /job/{job_id} */
  getJob: (job_id: string) => api.get(`/job/${job_id}`),

  /** POST /job/{job_id}/cancel */
  cancelJob: (job_id: string) => api.post(`/job/${job_id}/cancel`),

  // ─── Demo Pipeline ───────────────────────────────────────
  /** SSE /demo/pipeline/stream - public, no auth */
  demoPipelineStreamUrl: (params?: Record<string, string | number | boolean>) =>
    sseUrl("/demo/pipeline/stream", params),
};
