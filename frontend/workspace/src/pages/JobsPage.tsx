import { useCancelJob, useExport, useListJobs, useUploadFile } from "@/hooks/useJobManager";
import { cn } from "@/lib/cn";
import { AlertTriangle, Download, FileUp, RefreshCw, X } from "lucide-react";
import { useRef, useState } from "react";

export function JobsPage() {
  const jobsQ = useListJobs();
  const cancelJob = useCancelJob();
  const uploadFile = useUploadFile();
  const exportData = useExport();
  const fileRef = useRef<HTMLInputElement>(null);
  const [exportForm, setExportForm] = useState({ entity: "audit_logs", format: "csv" as const });

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    await uploadFile.mutateAsync(file);
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Async Operations</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Jobs, Uploads & Exports</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Monitor async job queue, upload files, and export workspace data in CSV, JSON, or PDF.
        </p>
      </header>

      {/* Upload */}
      <section className="mb-8 frame p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <FileUp className="h-4 w-4 text-brass" /> Upload File
        </h2>
        <div className="flex items-center gap-3">
          <input ref={fileRef} type="file" onChange={handleUpload} className="hidden" id="file-upload" />
          <label
            htmlFor="file-upload"
            className={cn("flex cursor-pointer items-center gap-2 rounded-lg border border-rule px-4 py-2.5 text-sm text-bone hover:bg-white/[0.04]", uploadFile.isPending && "pointer-events-none opacity-50")}
          >
            <FileUp className="h-4 w-4" />
            {uploadFile.isPending ? "Uploading…" : "Choose file"}
          </label>
          {uploadFile.isSuccess && (
            <span className="text-xs text-moss">✓ Uploaded: {uploadFile.data?.filename}</span>
          )}
          {uploadFile.isError && (
            <span className="flex items-center gap-1 text-xs text-crimson">
              <AlertTriangle className="h-3 w-3" /> Upload failed — /upload may not be deployed yet.
            </span>
          )}
        </div>
      </section>

      {/* Export */}
      <section className="mb-8 frame p-5">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <Download className="h-4 w-4 text-brass" /> Export Data
        </h2>
        <div className="flex flex-wrap items-end gap-3">
          <label className="space-y-1">
            <span className="text-xs text-muted">Entity</span>
            <select value={exportForm.entity} onChange={(e) => setExportForm((f) => ({ ...f, entity: e.target.value }))} className="v-input">
              <option value="audit_logs">Audit logs</option>
              <option value="billing_transactions">Billing transactions</option>
              <option value="models">Models</option>
              <option value="pipelines">Pipelines</option>
              <option value="deployments">Deployments</option>
              <option value="compliance_evidence">Compliance evidence</option>
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs text-muted">Format</span>
            <select value={exportForm.format} onChange={(e) => setExportForm((f) => ({ ...f, format: e.target.value as typeof exportForm.format }))} className="v-input">
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
              <option value="pdf">PDF</option>
            </select>
          </label>
          <button
            type="button"
            onClick={() => exportData.mutate(exportForm)}
            disabled={exportData.isPending}
            className="v-btn-primary flex items-center gap-1.5 text-sm"
          >
            <Download className="h-3.5 w-3.5" />
            {exportData.isPending ? "Queuing…" : "Export"}
          </button>
          {exportData.isSuccess && (
            <span className="text-xs text-moss">✓ Job queued: {exportData.data?.job_id}</span>
          )}
          {exportData.isError && (
            <span className="text-xs text-crimson">Export failed — /export may not be deployed yet.</span>
          )}
        </div>
      </section>

      {/* Job Queue */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <RefreshCw className="h-4 w-4 text-brass" /> Job Queue
        </h2>
        {jobsQ.isLoading ? (
          <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="frame h-14 animate-pulse bg-white/[0.02]" />)}</div>
        ) : jobsQ.isError ? (
          <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">Could not load jobs — /job may not be deployed yet.</div>
        ) : (jobsQ.data ?? []).length === 0 ? (
          <div className="frame border-dashed p-6 text-center text-sm text-muted">No jobs in queue.</div>
        ) : (
          <div className="frame overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-rule bg-white/[0.02] text-eyebrow">
                <tr>{["Type", "Status", "Progress", "Created", "Actions"].map((h) => <th key={h} className="px-4 py-3">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {(jobsQ.data ?? []).map((job) => (
                  <tr key={job.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-bone-2">{job.type}</td>
                    <td className="px-4 py-3"><JobStatusChip status={job.status} /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white/[0.06]">
                          <div className={cn("h-full rounded-full", job.status === "done" ? "bg-moss" : job.status === "failed" ? "bg-crimson" : "bg-brass")} style={{ width: `${job.progress_pct}%` }} />
                        </div>
                        <span className="font-mono text-xs text-muted">{job.progress_pct}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted">{new Date(job.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {job.result_url && (
                          <a href={job.result_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-brass-2 hover:underline">
                            <Download className="h-3 w-3" /> Download
                          </a>
                        )}
                        {(job.status === "queued" || job.status === "running") && (
                          <button type="button" onClick={() => cancelJob.mutate(job.id)} className="flex items-center gap-1 rounded border border-rule px-2 py-1 text-xs text-muted hover:text-crimson">
                            <X className="h-3 w-3" /> Cancel
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function JobStatusChip({ status }: { status: string }) {
  return (
    <span className={cn("v-chip",
      status === "done" && "v-chip-ok",
      status === "running" && "v-chip-brass",
      status === "failed" && "v-chip-err",
      status === "queued" && "v-chip-warn",
    )}>{status}</span>
  );
}
