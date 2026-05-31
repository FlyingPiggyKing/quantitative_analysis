import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TrendRun {
  id: number;
  run_date: string;
  trigger_type: "auto" | "manual";
  status: "pending" | "running" | "completed" | "cancelled" | "interrupted";
  current_batch: number;
  batch_count: number;
  batch_total: number;
  batch_completed: number;
}

export interface TrendRunStatus {
  run: TrendRun | null;
  manual_trigger_available: boolean;
  run_active: boolean;
  on_schedule: boolean;
  off_schedule_reason: string | null;
  disabled_reason: string | null;
}

export interface TriggerTrendRunResponse {
  run: TrendRun | null;
  run_id: number;
}

export async function getTrendRunStatus(): Promise<TrendRunStatus> {
  const res = await fetch(`${API_BASE}/api/admin/trend-run`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error("Failed to fetch trend run status");
  }
  return res.json();
}

export async function triggerTrendRun(): Promise<TriggerTrendRunResponse> {
  const res = await fetch(`${API_BASE}/api/admin/trend-run/trigger`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (res.status === 409) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "A run is already in progress");
  }
  if (!res.ok) {
    throw new Error("Failed to trigger trend run");
  }
  return res.json();
}
