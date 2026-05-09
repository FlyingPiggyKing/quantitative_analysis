"use client";

import { useState } from "react";
import { TrendPrediction, SentimentAnalysis, TechnicalAnalysis, TrendJudgment } from "@/services/trendPrediction";

interface TrendAnalysisPanelProps {
  prediction: TrendPrediction;
}

export default function TrendAnalysisPanel({ prediction }: TrendAnalysisPanelProps) {
  const { 情绪分析, 技术分析, 趋势判断 } = prediction;

  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    sentiment: false,
    technical: false,
    judgment: false,
  });

  const toggleSection = (key: string) => {
    setCollapsedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // If no extended analysis, show fallback message
  if (!情绪分析 && !技术分析 && !趋势判断) {
    return (
      <div className="vt-engraved py-2">
        <p>暂无详细分析数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 情绪分析 */}
      {情绪分析 && (
        <CollapsibleSection
          title="情绪分析"
          isCollapsed={collapsedSections.sentiment}
          onToggle={() => toggleSection("sentiment")}
        >
          <SentimentSection data={情绪分析} />
        </CollapsibleSection>
      )}

      {/* 技术分析 */}
      {技术分析 && (
        <CollapsibleSection
          title="技术分析"
          isCollapsed={collapsedSections.technical}
          onToggle={() => toggleSection("technical")}
        >
          <TechnicalSection data={技术分析} />
        </CollapsibleSection>
      )}

      {/* 趋势判断 */}
      {趋势判断 && (
        <CollapsibleSection
          title="趋势判断"
          isCollapsed={collapsedSections.judgment}
          onToggle={() => toggleSection("judgment")}
        >
          <TrendJudgmentSection data={趋势判断} />
        </CollapsibleSection>
      )}

      {/* Disclaimer */}
      <p className="vt-engraved text-xs mt-4">
        建议仅供参考，不作为投资依据
      </p>
    </div>
  );
}

function CollapsibleSection({
  title,
  children,
  isCollapsed,
  onToggle,
}: {
  title: string;
  children: React.ReactNode;
  isCollapsed: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="md:border-0">
      <button
        onClick={onToggle}
        className="w-full flex justify-between items-center p-3 md:p-0 min-h-[44px] active:opacity-80 md:active:opacity-100"
      >
        <span className="font-[var(--font-playfair)] tracking-[0.16em] uppercase text-vt-brass-400 text-sm">{title}</span>
        <span className="text-vt-brass-400 text-xl md:hidden font-[var(--font-playfair)]">{isCollapsed ? "+" : "−"}</span>
      </button>
      <div className={`${isCollapsed ? "hidden" : "block"} md:block`}>
        {children}
      </div>
    </div>
  );
}

function SentimentSection({ data }: { data: SentimentAnalysis }) {
  return (
    <div className="pt-2">
      {/* News list */}
      {data.news && data.news.length > 0 ? (
        <div className="space-y-2 mb-3">
          {data.news.slice(0, 5).map((news, idx) => (
            <div key={idx} className="text-xs">
              <div className="flex items-start gap-2">
                <span className="text-vt-parchment-dim font-[var(--font-geist-mono)] whitespace-nowrap">{news.date}</span>
                <div>
                  <span className="text-vt-brass-300">{news.title}</span>
                  <span className="text-vt-parchment-dim ml-2 italic">({news.source})</span>
                </div>
              </div>
              {news.summary && (
                <p className="text-vt-parchment-soft mt-1 pl-12">{news.summary}</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="vt-engraved text-xs mb-2">暂无新闻数据</p>
      )}

      {/* Summary */}
      {data.summary && (
        <div className="text-sm text-vt-parchment rounded p-3" style={{ background: "rgba(40,32,22,0.6)", border: "1px solid rgba(120,95,50,0.2)" }}>
          {data.summary}
        </div>
      )}
    </div>
  );
}

function TechnicalSection({ data }: { data: TechnicalAnalysis }) {
  const cardStyle = {
    background: "rgba(40,32,22,0.6)",
    border: "1px solid rgba(120,95,50,0.2)",
  };
  return (
    <div className="pt-2">
      <div className="grid grid-cols-2 gap-2 text-xs">
        {/* MACD */}
        {data.macd && (
          <div className="rounded p-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">MACD:</span>
            <span className="ml-1 text-vt-parchment font-[var(--font-geist-mono)]">{data.macd.value || "-"}</span>
            <span className={`ml-2 font-[var(--font-playfair)] ${
              data.macd.signal?.includes("金叉") ? "text-vt-oxblood-400" : "text-vt-emerald-400"
            }`}>
              {data.macd.signal || "-"}
            </span>
            {data.macd.interpretation && (
              <p className="text-vt-parchment-soft mt-1">{data.macd.interpretation}</p>
            )}
          </div>
        )}

        {/* RSI */}
        {data.rsi && (
          <div className="rounded p-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">RSI:</span>
            <span className="ml-1 text-vt-parchment font-[var(--font-geist-mono)]">{data.rsi.value || "-"}</span>
            <span className={`ml-2 font-[var(--font-playfair)] ${
              data.rsi.zone?.includes("超买") ? "text-vt-oxblood-400" :
              data.rsi.zone?.includes("超卖") ? "text-vt-emerald-400" : "text-vt-parchment-dim"
            }`}>
              {data.rsi.zone || "-"}
            </span>
            {data.rsi.interpretation && (
              <p className="text-vt-parchment-soft mt-1">{data.rsi.interpretation}</p>
            )}
          </div>
        )}

        {/* MA */}
        {data.ma && (
          <div className="rounded p-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">均线:</span>
            <span className="ml-1 text-vt-parchment">{data.ma.position || "-"}</span>
            {data.ma.interpretation && (
              <p className="text-vt-parchment-soft mt-1">{data.ma.interpretation}</p>
            )}
          </div>
        )}

        {/* Volume */}
        {data.volume && (
          <div className="rounded p-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">成交量:</span>
            <span className="ml-1 text-vt-parchment font-[var(--font-geist-mono)]">{(Number(data.volume.ratio) || 0).toFixed(2)}</span>
            <span className={`ml-2 ${
              Number(data.volume.ratio) > 1 ? "text-vt-emerald-400" : "text-vt-parchment-dim"
            }`}>
              {data.volume.interpretation || "-"}
            </span>
          </div>
        )}

        {/* Valuation */}
        {data.valuation && (
          <div className="rounded p-2 col-span-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">估值:</span>
            {data.valuation.pe && <span className="ml-2 text-vt-parchment font-[var(--font-geist-mono)]">PE: {data.valuation.pe}</span>}
            {data.valuation.pb && <span className="ml-2 text-vt-parchment font-[var(--font-geist-mono)]">PB: {data.valuation.pb}</span>}
            {data.valuation.turnover && <span className="ml-2 text-vt-parchment font-[var(--font-geist-mono)]">换手: {data.valuation.turnover}%</span>}
            {data.valuation.interpretation && (
              <p className="text-vt-parchment-soft mt-1">{data.valuation.interpretation}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TrendJudgmentSection({ data }: { data: TrendJudgment }) {
  const suggestionColors: Record<string, string> = {
    "加仓": "text-vt-oxblood-400",
    "减仓": "text-vt-emerald-400",
    "持有": "text-vt-brass-300",
    "建仓": "text-vt-oxblood-400",
    "观望": "text-vt-parchment-dim",
  };

  // Parse multi-paragraph content with titles
  // Format: "标题\n内容\n\n标题\n内容"
  const renderParagraphs = (text: string) => {
    if (!text) return null;
    const paragraphs = text.split("\n\n").filter(p => p.trim());
    return paragraphs.map((para, idx) => {
      const lines = para.split("\n");
      const title = lines[0].trim();
      const content = lines.slice(1).join("\n").trim();
      return (
        <div key={idx} className="mb-2">
          <span className="text-vt-brass-400 font-[var(--font-playfair)] tracking-wide">{title}</span>
          {content && <p className="text-vt-parchment mt-1 leading-relaxed">{content}</p>}
        </div>
      );
    });
  };

  const innerStyle = { background: "rgba(40,32,22,0.6)", border: "1px solid rgba(120,95,50,0.2)" };

  return (
    <div className="pt-2 space-y-2">
      {/* Forecast */}
      {data.forecast && (
        <div className="text-sm">
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">走势预测:</span>
          <div className="mt-1 rounded p-3" style={innerStyle}>
            {renderParagraphs(data.forecast)}
          </div>
        </div>
      )}

      {/* Suggestion */}
      {data.suggestion && (
        <div className="text-sm">
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">操作建议:</span>
          <span
            className={`ml-2 text-xl font-[var(--font-playfair)] font-bold tracking-wide ${
              suggestionColors[data.suggestion] || "text-vt-parchment"
            }`}
            style={{ textShadow: "0 0 8px currentColor, 0 1px 0 rgba(0,0,0,0.6)" }}
          >
            {data.suggestion}
          </span>
        </div>
      )}

      {/* Reasoning */}
      {data.reasoning && (
        <div className="text-sm rounded p-3" style={innerStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">理由:</span>
          <div className="mt-1">
            {renderParagraphs(data.reasoning)}
          </div>
        </div>
      )}
    </div>
  );
}
