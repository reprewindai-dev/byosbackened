/**
 * useWorkspaceTraining
 *
 * Manage workspace ML model training.
 * Used in: Settings → Workspace Intelligence panel.
 *
 * Rules:
 *   - Do NOT trigger without checking sample count first.
 *   - Show: "Not enough samples" / "Ready to train" / "Training started" / "Last trained".
 *   - Do NOT promise better performance if sample_count < min_samples.
 *   - Disable train button while loading or if insufficient data.
 */
import { useState, useCallback } from "react";
import { autonomousService } from "@/lib/services/autonomous.service";

export type TrainingStatus =
  | "idle"
  | "insufficient_data"
  | "ready"
  | "training"
  | "complete"
  | "error";

export interface WorkspaceTrainingState {
  status: TrainingStatus;
  sampleCount: number;
  minSamples: number;
  lastTrainedAt: string | null;
  error: string | null;
  canTrain: boolean;
  statusLabel: string;
}

export function useWorkspaceTraining(minSamples = 100) {
  const [state, setState] = useState<WorkspaceTrainingState>({
    status: "idle",
    sampleCount: 0,
    minSamples,
    lastTrainedAt: null,
    error: null,
    canTrain: false,
    statusLabel: "Loading...",
  });

  const checkAndTrain = useCallback(async () => {
    setState((s) => ({ ...s, status: "training", error: null, statusLabel: "Training started..." }));
    try {
      const { data } = await autonomousService.trainWorkspace({ min_samples: minSamples });

      if (data.status === "insufficient_data") {
        setState((s) => ({
          ...s,
          status: "insufficient_data",
          canTrain: false,
          statusLabel: `Learning mode — needs ${minSamples - (s.sampleCount)} more runs`,
        }));
      } else if (data.status === "started") {
        setState((s) => ({
          ...s,
          status: "complete",
          canTrain: true,
          lastTrainedAt: new Date().toISOString(),
          statusLabel: `Training started — models: ${data.models_trained?.join(", ") ?? "updating"}`,
        }));
      } else {
        setState((s) => ({
          ...s,
          status: "complete",
          statusLabel: data.message,
        }));
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Training failed";
      setState((s) => ({ ...s, status: "error", error: msg, statusLabel: "Training failed" }));
    }
  }, [minSamples]);

  return { ...state, train: checkAndTrain };
}
