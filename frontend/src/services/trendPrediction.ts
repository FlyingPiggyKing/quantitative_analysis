const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TrendPrediction {
  symbol: string;
  name: string;
  trend_direction: "up" | "down" | "neutral";
  confidence: number;
  summary: string;
  analyzed_at: string;
}

export interface BatchAnalysisResponse {
  analyzed: number;
  failed: number;
  results: TrendPrediction[];
}

export interface BatchAsyncResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: string;
  current: number;
  total: number;
  results?: TrendPrediction[];
  error?: string;
}

export async function getTrendPredictions(): Promise<TrendPrediction[]> {
  const res = await fetch(`${API_BASE}/api/trend-predictions`);
  if (!res.ok) {
    throw new Error("Failed to fetch trend predictions");
  }
  return res.json();
}

export async function getTrendPrediction(symbol: string): Promise<TrendPrediction | null> {
  const res = await fetch(`${API_BASE}/api/trend-predictions/${symbol}`);
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error("Failed to fetch trend prediction");
  }
  return res.json();
}

export async function runBatchAnalysis(): Promise<BatchAnalysisResponse> {
  const res = await fetch(`${API_BASE}/api/trend-predictions/batch`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error("Failed to run batch analysis");
  }
  return res.json();
}

export async function runBatchAnalysisAsync(): Promise<BatchAsyncResponse> {
  const res = await fetch(`${API_BASE}/api/trend-predictions/batch-async`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error("Failed to submit batch analysis");
  }
  return res.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await fetch(`${API_BASE}/api/trend-predictions/task/${taskId}`);
  if (!res.ok) {
    throw new Error("Failed to get task status");
  }
  return res.json();
}

export async function pollTaskStatus(
  taskId: string,
  onProgress?: (status: TaskStatusResponse) => void,
  intervalMs: number = 2000
): Promise<TaskStatusResponse> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getTaskStatus(taskId);
        if (onProgress) {
          onProgress(status);
        }
        if (status.status === "completed" || status.status === "failed") {
          resolve(status);
          return;
        }
      } catch (err) {
        reject(err);
        return;
      }
      setTimeout(poll, intervalMs);
    };
    poll();
  });
}
