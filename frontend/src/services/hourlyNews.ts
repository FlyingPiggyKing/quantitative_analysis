import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Top3NewsItem {
  news_title: string;
  summary: string;
  impact_reason: string;
}

export interface MarketImpact {
  direction: "流入偏多" | "流出偏多" | "中性";
  reason: string;
}

export interface SectorImpactItem {
  sector: string;
  reason: string;
}

export interface HourlyNewsSummary {
  hour: string;
  hour_timestamp: string;
  top3_news: Top3NewsItem[];
  market_impact: MarketImpact;
  sector_impact: SectorImpactItem[];
  created_at: string;
}

export async function getHourlyNews(limit: number = 3): Promise<HourlyNewsSummary[]> {
  const res = await fetch(`${API_BASE}/api/hourly_news?limit=${limit}`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch hourly news");
  }
  return res.json();
}

export async function getLatestHourlyNews(): Promise<HourlyNewsSummary | null> {
  const res = await fetch(`${API_BASE}/api/hourly_news/latest`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch latest hourly news");
  }
  const data = await res.json();
  if (!data.hour) {
    return null;
  }
  return data;
}
