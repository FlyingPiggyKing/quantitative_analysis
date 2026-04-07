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
