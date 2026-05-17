import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface Plugin {
  id: string;
  slug: string;
  name: string;
  version: string;
  author: string;
  category: string;
  description: string;
  installed: boolean;
  enabled: boolean;
  config_schema: Record<string, unknown>;
  config_values: Record<string, unknown>;
  marketplace_url?: string;
}

export function usePlugins() {
  return useQuery<Plugin[]>({
    queryKey: ["plugins"],
    queryFn: async () => {
      const { data } = await api.get("/plugins");
      return Array.isArray(data) ? data : data?.plugins || [];
    },
  });
}

export function useInstallPlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (slug: string) => {
      const { data } = await api.post(`/plugins/${slug}/install`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plugins"] }),
  });
}

export function useUninstallPlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (slug: string) => {
      const { data } = await api.delete(`/plugins/${slug}`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plugins"] }),
  });
}

export function useTogglePlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ slug, enabled }: { slug: string; enabled: boolean }) => {
      const { data } = await api.patch(`/plugins/${slug}`, { enabled });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plugins"] }),
  });
}

export function useUpdatePluginConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ slug, config }: { slug: string; config: Record<string, string> }) => {
      const { data } = await api.patch(`/plugins/${slug}`, { config });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plugins"] }),
  });
}
