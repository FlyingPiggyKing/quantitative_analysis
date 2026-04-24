import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SentimentAnalysis {
  news: Array<{
    title: string;
    source: string;
    date: string;
    summary: string;
  }>;
  summary: string;
}

export interface TechnicalAnalysis {
  macd: {
    value: string;
    signal: string;
    interpretation: string;
  };
  rsi: {
    value: string;
    zone: string;
    interpretation: string;
  };
  ma: {
    position: string;
    interpretation: string;
  };
  volume: {
    ratio: string;
    interpretation: string;
  };
  valuation?: {
    pe: string;
    pb: string;
    turnover: string;
    interpretation: string;
  };
}

export interface TrendJudgment {
  forecast: string;
  suggestion: "加仓" | "减仓" | "持有" | "建仓" | "观望";
  reasoning: string;
}

export interface TrendPrediction {
  symbol: string;
  name: string;
  trend_direction: "up" | "down" | "neutral";
  confidence: number;
  summary: string;
  analyzed_at: string;
  情绪分析?: SentimentAnalysis | null;
  技术分析?: TechnicalAnalysis | null;
  趋势判断?: TrendJudgment | null;
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
    headers: {
      ...getAuthHeaders(),
    },
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

export async function runForcedSingleAnalysis(symbol: string): Promise<TrendPrediction> {
  const res = await fetch(`${API_BASE}/api/trend-predictions/${symbol}?force=true`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (res.status === 429) {
    const data = await res.json().catch(() => ({}));
    const retryAfter = data.retry_after || parseInt(res.headers.get("retry_after") || "0", 10);
    const error = new Error(`Rate limit exceeded. Try again in ${retryAfter} seconds.`) as Error & { retryAfter?: number };
    error.retryAfter = retryAfter;
    throw error;
  }
  if (!res.ok) {
    throw new Error("Failed to run forced analysis");
  }
  return res.json();
}

const COOLDOWN_KEY_PREFIX = "analysis_cooldown";

function getCooldownKey(userId: string, symbol: string): string {
  return `${COOLDOWN_KEY_PREFIX}_${userId}_${symbol}`;
}

export function setCooldownEndTime(userId: string, symbol: string, endTime: number): void {
  if (typeof window === "undefined") return;
  const key = getCooldownKey(userId, symbol);
  localStorage.setItem(key, endTime.toString());
}

export function getCooldownEndTime(userId: string, symbol: string): number | null {
  if (typeof window === "undefined") return null;
  const key = getCooldownKey(userId, symbol);
  const value = localStorage.getItem(key);
  if (value === null) return null;
  const endTime = parseInt(value, 10);
  if (isNaN(endTime)) return null;
  return endTime;
}

export function clearCooldownEndTime(userId: string, symbol: string): void {
  if (typeof window === "undefined") return;
  const key = getCooldownKey(userId, symbol);
  localStorage.removeItem(key);
}
