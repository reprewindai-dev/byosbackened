import { useState } from "react";
import { Eye, EyeOff, PlusCircle, Shield, Trash2 } from "lucide-react";
import { useCreateRedactionRule, useDeleteRedactionRule, useRedactionRules, useToggleRedactionRule } from "@/hooks/usePrivacyAndSafety";
import { cn } from "@/lib/cn";

export function PrivacyPage() {
  const rulesQ = useRedactionRules();
  const createRule = useCreateRedactionRule();
  const toggleRule = useToggleRedactionRule();
  const deleteRule = useDeleteRedactionRule();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", pattern_type: "entity_type" as const, pattern: "EMAIL", entity_type: "PII" as const, replacement: "[REDACTED]", enabled: true });

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Privacy</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">PHI / PII Redaction Rules</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Define regex patterns, entity types, or keywords that will be automatically redacted from all AI inputs and outputs.
        </p>
      </header>

      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm text-muted">{(rulesQ.data ?? []).length} rule{(rulesQ.data ?? []).length !== 1 ? "s" : ""} active</span>
        <button type="button" onClick={() => setShowForm((v) => !v)} className="flex items-center gap-1.5 rounded-lg border border-rule px-3 py-1.5 text-xs text-bone hover:bg-white/[0.04]">
          <PlusCircle className="h-3.5 w-3.5" /> New rule
        </button>
      </div>

      {showForm && (
        <form
          className="frame mb-4 grid gap-4 p-4 md:grid-cols-2"
          onSubmit={async (e) => { e.preventDefault(); await createRule.mutateAsync(form); setShowForm(false); }}
        >
          <label className="space-y-1 md:col-span-2">
            <span className="text-xs text-muted">Rule name</span>
            <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required className="v-input w-full" placeholder="e.g. Redact patient emails" />
          </label>
          <label className="space-y-1">
            <span className="text-xs text-muted">Pattern type</span>
            <select value={form.pattern_type} onChange={(e) => setForm((f) => ({ ...f, pattern_type: e.target.value as typeof form.pattern_type }))} className="v-input w-full">
              <option value="entity_type">Entity type</option>
              <option value="regex">Regex</option>
              <option value="keyword">Keyword</option>
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs text-muted">Pattern / Entity</span>
            <input value={form.pattern} onChange={(e) => setForm((f) => ({ ...f, pattern: e.target.value }))} required className="v-input w-full" placeholder="EMAIL, PHONE, or regex" />
          </label>
          <label className="space-y-1">
            <span className="text-xs text-muted">Entity type</span>
            <select value={form.entity_type} onChange={(e) => setForm((f) => ({ ...f, entity_type: e.target.value as typeof form.entity_type }))} className="v-input w-full">
              <option value="PHI">PHI</option>
              <option value="PII">PII</option>
              <option value="PCI">PCI</option>
              <option value="custom">Custom</option>
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs text-muted">Replacement text</span>
            <input value={form.replacement} onChange={(e) => setForm((f) => ({ ...f, replacement: e.target.value }))} className="v-input w-full" />
          </label>
          <div className="md:col-span-2 flex gap-3">
            <button type="submit" disabled={createRule.isPending} className="v-btn-primary text-sm">{createRule.isPending ? "Saving…" : "Create rule"}</button>
            <button type="button" onClick={() => setShowForm(false)} className="v-btn text-sm">Cancel</button>
          </div>
        </form>
      )}

      {rulesQ.isLoading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="frame h-14 animate-pulse bg-white/[0.02]" />)}</div>
      ) : rulesQ.isError ? (
        <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">Could not load redaction rules — /privacy/rules may not be deployed yet.</div>
      ) : (rulesQ.data ?? []).length === 0 ? (
        <div className="frame border-dashed p-8 text-center text-sm text-muted">
          <Shield className="mx-auto mb-3 h-8 w-8 text-muted" />
          No redaction rules configured. Add one to start protecting PHI/PII.
        </div>
      ) : (
        <div className="space-y-2">
          {(rulesQ.data ?? []).map((rule) => (
            <div key={rule.id} className={cn("frame flex items-center justify-between gap-4 p-4", !rule.enabled && "opacity-50")}>
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-bone">{rule.name}</div>
                <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                  <span className="font-mono">{rule.pattern}</span>
                  <span>→</span>
                  <span className="font-mono text-brass-2">{rule.replacement}</span>
                  <span className="v-chip">{rule.entity_type}</span>
                  <span className="v-chip">{rule.pattern_type}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button type="button" onClick={() => toggleRule.mutate({ id: rule.id, enabled: !rule.enabled })} aria-label={rule.enabled ? "Disable rule" : "Enable rule"} className="text-muted hover:text-bone">
                  {rule.enabled ? <Eye className="h-4 w-4 text-moss" /> : <EyeOff className="h-4 w-4" />}
                </button>
                <button type="button" onClick={() => deleteRule.mutate(rule.id)} aria-label="Delete rule" className="text-muted hover:text-crimson">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
