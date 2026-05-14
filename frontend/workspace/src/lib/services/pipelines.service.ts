import { api, sseUrl } from "@/lib/api";

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

  /** POST /pipelines/{pipeline_id}/stop */
  stop: (pipeline_id: string) => api.post(`/pipelines/${pipeline_id}/stop`),

  /** GET /pipelines/{pipeline_id}/runs */
  listRuns: (pipeline_id: string, params?: { page?: number; limit?: number }) =>
    api.get(`/pipelines/${pipeline_id}/runs`, { params }),

  /** GET /pipelines/{pipeline_id}/runs/{run_id} */
  getRun: (pipeline_id: string, run_id: string) =>
    api.get(`/pipelines/${pipeline_id}/runs/${run_id}`),

  /** SSE /pipelines/{pipeline_id}/runs/{run_id}/stream */
  runStreamUrl: (pipeline_id: string, run_id: string) =>
    sseUrl(`/pipelines/${pipeline_id}/runs/${run_id}/stream`),

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

  /** POST /deployments/{deployment_id}/scale */
  scaleDeployment: (deployment_id: string, body: { replicas: number }) =>
    api.post(`/deployments/${deployment_id}/scale`, body),

  /** POST /deployments/{deployment_id}/restart */
  restartDeployment: (deployment_id: string) =>
    api.post(`/deployments/${deployment_id}/restart`),

  /** GET /deployments/{deployment_id}/logs */
  getDeploymentLogs: (deployment_id: string, params?: { from?: string; limit?: number }) =>
    api.get(`/deployments/${deployment_id}/logs`, { params }),

  // ─── Jobs ────────────────────────────────────────────────
  /** GET /jobs */
  listJobs: (params?: { status?: string; page?: number; limit?: number }) =>
    api.get("/jobs", { params }),

  /** GET /jobs/{job_id} */
  getJob: (job_id: string) => api.get(`/jobs/${job_id}`),

  /** DELETE /jobs/{job_id} */
  cancelJob: (job_id: string) => api.delete(`/jobs/${job_id}`),

  // ─── Demo Pipeline ───────────────────────────────────────
  /** SSE /demo/pipeline/stream - public, no auth */
  demoPipelineStreamUrl: (params?: Record<string, string | number | boolean>) =>
    sseUrl("/demo/pipeline/stream", params),
};
