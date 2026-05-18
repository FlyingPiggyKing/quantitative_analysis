import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface InstitutionalTrendPrediction {
  symbol: string;
  name: string;
  trend_direction: "up" | "down" | "neutral";
  confidence: number;
  summary: string;
  analyzed_at: string;
  is_fallback?: boolean;
  宏观产业周期?: {
    macro_summary: string;
    industry_cycle: string;
    policy_impact: string;
  };
  板块行业景气?: {
    sector_momentum: string;
    prosperity_trend: string;
    leading_stocks: string;
  };
  公司基本面质变?: {
    business_change: string;
    recent_events: string;
    fundamental_assessment: string;
  };
  资金筹码结构?: {
    dragon_tiger_net: string;
    institutional_strength: string;
    main_force_flow: string;
    seat_distribution: string;
    retail_vs_institutional: string;
  };
  技术形态量价?: {
    kline_pattern: string;
    macd: { value: string; signal: string; interpretation: string };
    rsi: { value: string; zone: string; interpretation: string };
    ma: { position: string; interpretation: string };
    volume: { ratio: string; interpretation: string };
    valuation: { pe: string; pb: string; turnover: string; market_cap: string; interpretation: string };
  };
  波段操作执行?: {
    第一轮短线: {
      direction: string;
      timeframe: string;
      entry_price: string;
      stop_loss: string;
      target_price: string;
      risk_reward: string;
    };
    第二轮中线: {
      direction: string;
      timeframe: string;
      entry_price: string;
      stop_loss: string;
      target_price: string;
      risk_reward: string;
    };
  };
  综合判断?: {
    short_term_outlook: string;
    medium_term_outlook: string;
    investment_tier: string;
    key_risks: string;
    reasoning: string;
  };
}

export interface TaskStatusResponse {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: string;
  current: number;
  total: number;
  results?: InstitutionalTrendPrediction[];
  error?: string;
}

export interface ForceAnalysisResponse {
  task_id: string;
  status: string;
}

export async function getInstitutionalPrediction(symbol: string): Promise<InstitutionalTrendPrediction | null> {
  const res = await fetch(`${API_BASE}/api/institutional-analysis/${symbol}`);
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error("Failed to fetch institutional prediction");
  }
  return res.json();
}

export async function runInstitutionalAnalysisAsync(symbol: string): Promise<ForceAnalysisResponse> {
  const res = await fetch(`${API_BASE}/api/institutional-analysis/${symbol}/force-async`, {
    method: "POST",
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
    throw new Error("Failed to submit institutional analysis");
  }
  return res.json();
}

export async function getInstitutionalAnalysisTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await fetch(`${API_BASE}/api/institutional-analysis/task/${taskId}`);
  if (!res.ok) {
    throw new Error("Failed to get task status");
  }
  return res.json();
}

export function pollInstitutionalAnalysisTaskStatus(
  taskId: string,
  onProgress?: (status: TaskStatusResponse) => void,
  intervalMs: number = 3000
): Promise<TaskStatusResponse> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getInstitutionalAnalysisTaskStatus(taskId);
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

const COOLDOWN_KEY_PREFIX = "institutional_analysis_cooldown";

function getCooldownKey(userId: string, symbol: string): string {
  return `${COOLDOWN_KEY_PREFIX}_${userId}_${symbol}`;
}

export function setInstitutionalCooldownEndTime(userId: string, symbol: string, endTime: number): void {
  if (typeof window === "undefined") return;
  const key = getCooldownKey(userId, symbol);
  localStorage.setItem(key, endTime.toString());
}

export function getInstitutionalCooldownEndTime(userId: string, symbol: string): number | null {
  if (typeof window === "undefined") return null;
  const key = getCooldownKey(userId, symbol);
  const value = localStorage.getItem(key);
  if (value === null) return null;
  const endTime = parseInt(value, 10);
  if (isNaN(endTime)) return null;
  return endTime;
}

export function clearInstitutionalCooldownEndTime(userId: string, symbol: string): void {
  if (typeof window === "undefined") return;
  const key = getCooldownKey(userId, symbol);
  localStorage.removeItem(key);
}
