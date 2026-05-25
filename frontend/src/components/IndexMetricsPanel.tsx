"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchIndexMetrics, fetchIndexHistory, fetchIndexList, fetchIndustryList, fetchSubIndustryList, IndexMetricData, IndexInfo, PEHistoryItem, IndustryInfo, SubIndustryInfo } from "@/services/indexMetrics";
import PEHistoryChart from "./PEHistoryChart";

type TimeRange = 5 | 10;

interface IndexCardProps {
  index: IndexInfo;
  years: TimeRange;
  onYearsChange: (ts_code: string, years: TimeRange) => void;
}

function getValuationStatus(percentile: number | null): { label: string; color: string; bg: string } {
  if (percentile === null) return { label: "—", color: "text-vt-parchment", bg: "bg-vt-ink-700" };
  if (percentile < 30) return { label: "低估", color: "text-vt-emerald-400", bg: "bg-vt-emerald-900/30" };
  if (percentile > 70) return { label: "高估", color: "text-vt-oxblood-400", bg: "bg-vt-oxblood-900/30" };
  return { label: "正常", color: "text-vt-brass-300", bg: "bg-vt-brass-900/30" };
}

function MetricCell({
  label,
  value,
  color,
  suffix,
}: {
  label: string;
  value: number | string | null;
  color?: string;
  suffix?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-1.5 px-1">
      <span className="vt-engraved not-italic text-[10px] tracking-[0.12em] uppercase whitespace-nowrap mb-0.5">
        {label}
      </span>
      <span className={`font-[var(--font-geist-mono)] text-sm font-medium ${color || "text-vt-parchment"}`}>
        {value !== null ? `${value}${suffix || ""}` : "--"}
      </span>
    </div>
  );
}

function IndexCard({ index, years, onYearsChange }: IndexCardProps) {
  const [data, setData] = useState<IndexMetricData | null>(null);
  const [history, setHistory] = useState<PEHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setHistoryLoading(true);
    setError(null);
    try {
      const [metricsResult, historyResult] = await Promise.all([
        fetchIndexMetrics(index.ts_code, years),
        fetchIndexHistory(index.ts_code, years),
      ]);

      if (metricsResult.error) {
        setError(metricsResult.error);
      } else {
        setData(metricsResult);
      }

      if (historyResult.data) {
        setHistory(historyResult.data);
      }
    } catch (err) {
      setError("加载失败");
    } finally {
      setLoading(false);
      setHistoryLoading(false);
    }
  }, [index.ts_code, years]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const status = getValuationStatus(data?.current_percentile ?? null);
  const displayName = data?.name || index.name;

  return (
    <div className="vt-panel p-3 sm:p-4 mb-3">
      {/* Header row: name | code | status | controls */}
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-2 active:opacity-80 min-w-0 flex-1"
        >
          <h3 className="font-[var(--font-playfair)] text-base sm:text-lg tracking-[0.08em] text-vt-parchment truncate">
            {displayName}
          </h3>
          <span className="vt-engraved not-italic text-[10px] tracking-wider whitespace-nowrap hidden sm:inline">
            {index.ts_code}
          </span>
          {data && (
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium tracking-wider ${status.color} ${status.bg} whitespace-nowrap`}>
              {status.label}
            </span>
          )}
        </button>

        {/* Inline controls */}
        <div className="flex items-center gap-1.5 shrink-0">
          <select
            value={years}
            onChange={(e) => onYearsChange(index.ts_code, parseInt(e.target.value) as TimeRange)}
            className="vt-input text-[11px] px-1.5"
            style={{ height: "28px", lineHeight: "1" }}
          >
            <option value={5}>5 年</option>
            <option value={10}>10 年</option>
          </select>
          <button
            onClick={loadData}
            disabled={loading}
            aria-label="刷新"
            title="刷新"
            className="vt-btn-secondary flex items-center justify-center p-0"
            style={{ height: "28px", width: "28px", minHeight: "28px", minWidth: "28px" }}
          >
            <svg
              className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 12a9 9 0 0 1-15.36 6.36L3 16" />
              <path d="M3 12a9 9 0 0 1 15.36-6.36L21 8" />
              <polyline points="3 21 3 16 8 16" />
              <polyline points="21 3 21 8 16 8" />
            </svg>
          </button>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="text-vt-brass-400 text-base font-[var(--font-playfair)] leading-none flex items-center justify-center"
            style={{ height: "28px", width: "20px", minHeight: "28px", minWidth: "20px" }}
            aria-label={collapsed ? "展开" : "收起"}
          >
            {collapsed ? "+" : "−"}
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          {loading && !data && (
            <div className="text-center py-6 vt-engraved text-sm">加 载 中 …</div>
          )}

          {error && !data && (
            <div className="text-center py-4 text-vt-oxblood-400 text-sm">{error}</div>
          )}

          {data && (
            <>
              {/* Metrics grid - responsive: 3 cols on mobile, 6 on desktop */}
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-1 sm:gap-2 mb-3 border-y border-vt-brass-500/20 py-2">
                <MetricCell
                  label="当前 PE"
                  value={data.current_pe?.toFixed(1) ?? null}
                  color="text-vt-brass-300"
                />
                <MetricCell
                  label="百分位"
                  value={data.current_percentile?.toFixed(1) ?? null}
                  suffix="%"
                  color={status.color}
                />
                <MetricCell
                  label="机会值"
                  value={data.opportunity?.toFixed(1) ?? null}
                  color="text-vt-emerald-400"
                />
                <MetricCell
                  label="危险值"
                  value={data.danger?.toFixed(1) ?? null}
                  color="text-vt-oxblood-400"
                />
                <MetricCell
                  label="历史最低"
                  value={data.historical_low?.toFixed(1) ?? null}
                />
                <MetricCell
                  label="历史最高"
                  value={data.historical_high?.toFixed(1) ?? null}
                />
              </div>

              {/* PE History Chart */}
              <div>
                {historyLoading ? (
                  <div className="h-[140px] sm:h-[160px] flex items-center justify-center vt-engraved text-xs">
                    图 表 加 载 中 …
                  </div>
                ) : history.length > 0 ? (
                  <PEHistoryChart
                    data={history}
                    opportunity={data.opportunity}
                    danger={data.danger}
                    height={140}
                  />
                ) : (
                  <div className="h-[140px] flex items-center justify-center vt-engraved text-xs">
                    暂 无 图 表 数 据
                  </div>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default function IndexMetricsPanel() {
  const [indices, setIndices] = useState<IndexInfo[]>([]);
  const [yearsMap, setYearsMap] = useState<Record<string, TimeRange>>({});
  const [loading, setLoading] = useState(true);

  // Industry selection state
  const [industries, setIndustries] = useState<IndustryInfo[]>([]);
  const [selectedIndustry, setSelectedIndustry] = useState<string>("");
  const [subIndustries, setSubIndustries] = useState<SubIndustryInfo[]>([]);
  const [selectedSubIndustry, setSelectedSubIndustry] = useState<string>("");
  const [subIndustryLoading, setSubIndustryLoading] = useState(false);
  const [industryHistory, setIndustryHistory] = useState<PEHistoryItem[]>([]);
  const [industryMetrics, setIndustryMetrics] = useState<IndexMetricData | null>(null);
  const [industryLoading, setIndustryLoading] = useState(false);
  const [industryYears, setIndustryYears] = useState<TimeRange>(10);

  useEffect(() => {
    async function loadIndices() {
      try {
        const [indicesResult, industriesResult] = await Promise.all([
          fetchIndexList(),
          fetchIndustryList(),
        ]);
        if (indicesResult.indices) {
          setIndices(indicesResult.indices);
        }
        if (industriesResult.industries) {
          setIndustries(industriesResult.industries);
          if (industriesResult.industries.length > 0) {
            const defaultIndustry =
              industriesResult.industries.find((i) => i.name === "有色金属") ??
              industriesResult.industries[0];
            setSelectedIndustry(defaultIndustry.ts_code);
            setSelectedSubIndustry(""); // Default to "行业汇总"
          }
        }
      } catch (err) {
        console.error("Failed to load indices:", err);
      } finally {
        setLoading(false);
      }
    }
    loadIndices();
  }, []);

  // Load industry data (metrics + history) when selection changes
  useEffect(() => {
    if (!selectedIndustry) return;

    // Determine which ts_code to use: sub-industry if selected, otherwise Level-1
    const targetTsCode = selectedSubIndustry || selectedIndustry;

    async function loadIndustryData() {
      setIndustryLoading(true);
      try {
        const [metricsResult, historyResult] = await Promise.all([
          fetchIndexMetrics(targetTsCode, industryYears),
          fetchIndexHistory(targetTsCode, industryYears),
        ]);
        if (metricsResult && !metricsResult.error) {
          setIndustryMetrics(metricsResult);
        }
        if (historyResult.data) {
          setIndustryHistory(historyResult.data);
        }
      } catch (err) {
        console.error("Failed to load industry data:", err);
      } finally {
        setIndustryLoading(false);
      }
    }
    loadIndustryData();
  }, [selectedIndustry, selectedSubIndustry, industryYears]);

  // Fetch sub-industries when Level-1 industry changes
  useEffect(() => {
    if (!selectedIndustry) return;

    async function loadSubIndustries() {
      setSubIndustryLoading(true);
      try {
        const result = await fetchSubIndustryList(selectedIndustry);
        if (result.sub_industries) {
          setSubIndustries(result.sub_industries);
        }
      } catch (err) {
        console.error("Failed to load sub-industries:", err);
      } finally {
        setSubIndustryLoading(false);
      }
    }
    loadSubIndustries();
  }, [selectedIndustry]);

  const handleYearsChange = useCallback((ts_code: string, years: TimeRange) => {
    setYearsMap((prev) => ({ ...prev, [ts_code]: years }));
  }, []);

  const selectedIndustryInfo = industries.find(i => i.ts_code === selectedIndustry);
  const industryStatus = getValuationStatus(industryMetrics?.current_percentile ?? null);
  const status = industryStatus;

  if (loading) {
    return (
      <div className="mt-4">
        <div className="text-center py-8 vt-engraved">加 载 中 …</div>
      </div>
    );
  }

  return (
    <div className="mt-4">
      {/* Industry PE Section - moved to top */}
      <div className="mb-4">
        <div className="flex items-end justify-between mb-2 px-1 gap-3">
          <div className="flex-1 min-w-0">
            <h2 className="vt-engraved not-italic text-[13px] sm:text-sm tracking-[0.16em] text-vt-brass-300 leading-tight truncate">
              行业估值 · PE 百分位
            </h2>
            <div
              className="mt-1 h-px w-12 sm:w-16"
              style={{
                background:
                  "linear-gradient(90deg, var(--vt-brass-600) 0%, transparent 100%)",
              }}
            />
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <select
              value={industryYears}
              onChange={(e) => setIndustryYears(parseInt(e.target.value) as TimeRange)}
              className="vt-input text-[11px] px-1.5"
              style={{ height: "24px", lineHeight: "1" }}
            >
              <option value={5}>5 年</option>
              <option value={10}>10 年</option>
            </select>
          </div>
        </div>

        <div className="vt-panel p-3 sm:p-4">
          {/* Industry selector - two level cascading; stacks on mobile, inline on desktop */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 mb-3">
            {/* Level 1 */}
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <label className="vt-engraved not-italic text-[10px] tracking-[0.18em] whitespace-nowrap shrink-0 w-[4.5rem]">
                一 级 行 业
              </label>
              <select
                value={selectedIndustry}
                onChange={(e) => {
                  setSelectedIndustry(e.target.value);
                  setSelectedSubIndustry(""); // Reset to "行业汇总" when Level-1 changes
                }}
                className="vt-input text-[11px] px-2 flex-1 min-w-0"
                style={{ height: "28px", lineHeight: "1" }}
              >
                {industries.map((ind) => (
                  <option key={ind.ts_code} value={ind.ts_code}>
                    {ind.name}
                  </option>
                ))}
              </select>
            </div>
            {/* Level 2 */}
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <label className="vt-engraved not-italic text-[10px] tracking-[0.18em] whitespace-nowrap shrink-0 w-[4.5rem]">
                二 级 行 业
              </label>
              <select
                value={selectedSubIndustry}
                onChange={(e) => setSelectedSubIndustry(e.target.value)}
                disabled={!selectedIndustry || subIndustryLoading}
                className="vt-input text-[11px] px-2 flex-1 min-w-0"
                style={{ height: "28px", lineHeight: "1" }}
              >
                <option value="">行业汇总</option>
                {subIndustries.map((ind) => (
                  <option key={ind.ts_code} value={ind.ts_code}>
                    {ind.name}
                  </option>
                ))}
              </select>
              {industryMetrics && (
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium tracking-wider ${status.color} ${status.bg} whitespace-nowrap shrink-0`}>
                  {status.label}
                </span>
              )}
            </div>
          </div>

          {/* Metrics grid */}
          {industryMetrics && (
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-1 sm:gap-2 mb-3 border-y border-vt-brass-500/20 py-2">
              <MetricCell
                label="当前 PE"
                value={industryMetrics.current_pe?.toFixed(1) ?? null}
                color="text-vt-brass-300"
              />
              <MetricCell
                label="百分位"
                value={industryMetrics.current_percentile?.toFixed(1) ?? null}
                suffix="%"
                color={status.color}
              />
              <MetricCell
                label="机会值"
                value={industryMetrics.opportunity?.toFixed(1) ?? null}
                color="text-vt-emerald-400"
              />
              <MetricCell
                label="危险值"
                value={industryMetrics.danger?.toFixed(1) ?? null}
                color="text-vt-oxblood-400"
              />
              <MetricCell
                label="历史最低"
                value={industryMetrics.historical_low?.toFixed(1) ?? null}
              />
              <MetricCell
                label="历史最高"
                value={industryMetrics.historical_high?.toFixed(1) ?? null}
              />
            </div>
          )}

          {/* Industry PE Chart */}
          <div>
            {industryLoading ? (
              <div className="h-[140px] sm:h-[160px] flex items-center justify-center vt-engraved text-xs">
                图 表 加 载 中 …
              </div>
            ) : industryHistory.length > 0 ? (
              <PEHistoryChart
                data={industryHistory}
                opportunity={industryMetrics?.opportunity ?? null}
                danger={industryMetrics?.danger ?? null}
                height={140}
              />
            ) : (
              <div className="h-[140px] flex items-center justify-center vt-engraved text-xs">
                暂 无 图 表 数 据
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-end justify-between mb-2 px-1 gap-3">
        <div className="flex-1 min-w-0">
          <h2 className="vt-engraved not-italic text-[13px] sm:text-sm tracking-[0.16em] text-vt-brass-300 leading-tight truncate">
            热门指数估值 · PE 百分位
          </h2>
          <div
            className="mt-1 h-px w-12 sm:w-16"
            style={{
              background:
                "linear-gradient(90deg, var(--vt-brass-600) 0%, transparent 100%)",
            }}
          />
        </div>
      </div>
      {indices.map((index) => (
        <IndexCard
          key={index.ts_code}
          index={index}
          years={yearsMap[index.ts_code] || 10}
          onYearsChange={handleYearsChange}
        />
      ))}
    </div>
  );
}
