const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface WatchlistItem {
  symbol: string;
  name: string;
  added_at: string;
}

export interface WatchlistResponse {
  items: WatchlistItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export async function getWatchlist(page: number = 1, pageSize: number = 10): Promise<WatchlistResponse> {
  const res = await fetch(`${API_BASE}/api/watchlist?page=${page}&page_size=${pageSize}`);
  if (!res.ok) {
    throw new Error("Failed to fetch watchlist");
  }
  return res.json();
}

export async function addToWatchlist(symbol: string, name: string): Promise<WatchlistItem> {
  const res = await fetch(`${API_BASE}/api/watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, name }),
  });
  if (!res.ok) {
    if (res.status === 409) {
      throw new Error("Stock already in watchlist");
    }
    throw new Error("Failed to add to watchlist");
  }
  return res.json();
}

export async function removeFromWatchlist(symbol: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/watchlist/${symbol}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error("Stock not in watchlist");
    }
    throw new Error("Failed to remove from watchlist");
  }
}

export async function checkWatchlist(symbol: string): Promise<WatchlistItem | null> {
  const res = await fetch(`${API_BASE}/api/watchlist/${symbol}`);
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error("Failed to check watchlist");
  }
  return res.json();
}
