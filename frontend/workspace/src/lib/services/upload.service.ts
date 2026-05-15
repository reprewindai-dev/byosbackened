import { api, noRoute } from "@/lib/api";

export const uploadService = {
  /** POST /upload - multipart file upload */
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
      },
    });
  },

  /** POST /upload, then POST /transcribe with uploaded asset_id */
  transcribe: async (file: File, params?: { language?: string; model?: string }) => {
    const uploaded = await uploadService.upload(file);
    return api.post("/transcribe", {
      asset_id: uploaded.data.id,
      language: params?.language,
      provider: params?.model,
    });
  },

  /** No route found: POST /extract multipart file; backend expects JSON text extraction */
  extract: (file: File, params?: { format?: string }) => {
    return noRoute("/extract multipart file", file, params);
  },

  /** No route found: GET /export/{job_id} */
  exportJob: (job_id: string, format?: string) =>
    noRoute(`/export/${job_id}`, format),
};
