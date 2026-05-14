/**
 * useJobManager — wires /api/v1/job/* + /api/v1/upload/* + /api/v1/export/*
 * Covers async job polling, file uploads, and export downloads.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type JobStatus = {
  id: string;
  type: string;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  progress_pct: number;
  result_url: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  workspace_id: string;
};

export type UploadedFile = {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  url: string;
  uploaded_at: string;
};

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: async () => (await api.get<JobStatus>(`/job/${jobId}`)).data,
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "failed" || status === "cancelled") return false;
      return 2_000;
    },
  });
}

export function useListJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: async () => (await api.get<JobStatus[]>("/job")).data,
    refetchInterval: 10_000,
  });
}

export function useCancelJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => api.post(`/job/${jobId}/cancel`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useUploadFile() {
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return (await api.post<UploadedFile>("/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })).data;
    },
  });
}

export function useExport() {
  return useMutation({
    mutationFn: async (payload: { entity: string; filters?: Record<string, unknown>; format: "csv" | "json" | "pdf" }) =>
      (await api.post<{ job_id: string }>("/export", payload)).data,
  });
}
