import { api } from "@/lib/api";

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

  /** POST /transcribe - audio/video to text */
  transcribe: (file: File, params?: { language?: string; model?: string }) => {
    const form = new FormData();
    form.append("file", file);
    if (params?.language) form.append("language", params.language);
    if (params?.model) form.append("model", params.model);
    return api.post("/transcribe", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  /** POST /extract - extract text/data from document */
  extract: (file: File, params?: { format?: string }) => {
    const form = new FormData();
    form.append("file", file);
    if (params?.format) form.append("format", params.format);
    return api.post("/extract", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  /** GET /export/{job_id} */
  exportJob: (job_id: string, format?: string) =>
    api.get(`/export/${job_id}`, { params: { format }, responseType: "blob" }),
};
