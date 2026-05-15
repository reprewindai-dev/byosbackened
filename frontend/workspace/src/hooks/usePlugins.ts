/**
 * usePlugins — wires /api/v1/plugins/* (plugin registry)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type Plugin = {
  id: string;
  slug: string;
  name: string;
  description: string;
  version: string;
  author: string;
  category: "integration" | "tool" | "model_adapter" | "compliance" | "monitoring";
  installed: boolean;
  enabled: boolean;
  config_schema: Record<string, unknown> | null;
  config_values: Record<string, unknown>;
  installed_at: string | null;
  updated_at: string;
  marketplace_url: string | null;
};

export function usePlugins() {
  return useQuery({
    queryKey: ["plugins"],
    queryFn: async () => (await api.get<Plugin[]>("/plugins")).data,
  });
}

export function useInstallPlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) => api.post<Plugin>(`/plugins/${slug}/enable`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plugins"] }),
  });
}

export function useUninstallPlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) => api.post<Plugin>(`/plugins/${slug}/disable`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plugins"] }),
  });
}

export function useTogglePlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, enabled }: { slug: string; enabled: boolean }) =>
      enabled ? api.post<Plugin>(`/plugins/${slug}/enable`, {}) : api.post<Plugin>(`/plugins/${slug}/disable`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plugins"] }),
  });
}

export function useUpdatePluginConfig() {
  return useMutation({
    mutationFn: async ({ slug }: { slug: string; config: Record<string, unknown> }) => {
      throw new Error(`Plugin config update is not exposed by the backend route contract for ${slug}`);
    },
  });
}
