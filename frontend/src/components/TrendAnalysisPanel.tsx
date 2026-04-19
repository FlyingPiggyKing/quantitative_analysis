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
      <div className="bg-slate-800 rounded-lg p-4 text-slate-400">
        <p>暂无详细分析数据</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg p-3 sm:p-4 space-y-4">
      <h3 className="text-lg font-medium text-white">AI 趋势分析</h3>

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
      <p className="text-xs text-slate-500 mt-4">
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
        className="w-full flex justify-between items-center p-3 md:p-0 min-h-[44px] active:opacity-70 md:active:opacity-100"
      >
        <span className="text-slate-300 font-medium">{title}</span>
        <span className="text-slate-400 text-xl md:hidden">{isCollapsed ? "+" : "−"}</span>
      </button>
      <div className={`${isCollapsed ? "hidden" : "block"} md:block`}>
        {children}
      </div>
    </div>
  );
}

function SentimentSection({ data }: { data: SentimentAnalysis }) {
  return (
    <div className="border border-slate-700 rounded p-3">
      <h4 className="text-sm font-medium text-slate-300 mb-2">情绪分析</h4>

      {/* News list */}
      {data.news && data.news.length > 0 ? (
        <div className="space-y-2 mb-3">
          {data.news.slice(0, 5).map((news, idx) => (
            <div key={idx} className="text-xs">
              <div className="flex items-start gap-2">
                <span className="text-slate-500 whitespace-nowrap">{news.date}</span>
                <div>
                  <span className="text-blue-400">{news.title}</span>
                  <span className="text-slate-500 ml-2">({news.source})</span>
                </div>
              </div>
              {news.summary && (
                <p className="text-slate-400 mt-1 pl-12">{news.summary}</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-slate-500 text-xs mb-2">暂无新闻数据</p>
      )}

      {/* Summary */}
      {data.summary && (
        <div className="text-sm text-slate-300 bg-slate-700/50 rounded p-2">
          {data.summary}
        </div>
      )}
    </div>
  );
}

function TechnicalSection({ data }: { data: TechnicalAnalysis }) {
  return (
    <div className="border border-slate-700 rounded p-3">
      <h4 className="text-sm font-medium text-slate-300 mb-2">技术分析</h4>

      <div className="grid grid-cols-2 gap-2 text-xs">
        {/* MACD */}
        {data.macd && (
          <div className="bg-slate-700/50 rounded p-2">
            <span className="text-slate-400">MACD:</span>
            <span className="ml-1 text-white">{data.macd.value || "-"}</span>
            <span className={`ml-2 ${
              data.macd.signal?.includes("金叉") ? "text-emerald-400" : "text-red-400"
            }`}>
              {data.macd.signal || "-"}
            </span>
            {data.macd.interpretation && (
              <p className="text-slate-400 mt-1">{data.macd.interpretation}</p>
            )}
          </div>
        )}

        {/* RSI */}
        {data.rsi && (
          <div className="bg-slate-700/50 rounded p-2">
            <span className="text-slate-400">RSI:</span>
            <span className="ml-1 text-white">{data.rsi.value || "-"}</span>
            <span className={`ml-2 ${
              data.rsi.zone?.includes("超买") ? "text-red-400" :
              data.rsi.zone?.includes("超卖") ? "text-emerald-400" : "text-slate-400"
            }`}>
              {data.rsi.zone || "-"}
            </span>
            {data.rsi.interpretation && (
              <p className="text-slate-400 mt-1">{data.rsi.interpretation}</p>
            )}
          </div>
        )}

        {/* MA */}
        {data.ma && (
          <div className="bg-slate-700/50 rounded p-2">
            <span className="text-slate-400">均线:</span>
            <span className="ml-1 text-white">{data.ma.position || "-"}</span>
            {data.ma.interpretation && (
              <p className="text-slate-400 mt-1">{data.ma.interpretation}</p>
            )}
          </div>
        )}

        {/* Volume */}
        {data.volume && (
          <div className="bg-slate-700/50 rounded p-2">
            <span className="text-slate-400">成交量:</span>
            <span className="ml-1 text-white">{(Number(data.volume.ratio) || 0).toFixed(2)}</span>
            <span className={`ml-2 ${
              Number(data.volume.ratio) > 1 ? "text-emerald-400" : "text-slate-400"
            }`}>
              {data.volume.interpretation || "-"}
            </span>
          </div>
        )}

        {/* Valuation */}
        {data.valuation && (
          <div className="bg-slate-700/50 rounded p-2 col-span-2">
            <span className="text-slate-400">估值:</span>
            {data.valuation.pe && <span className="ml-2 text-white">PE: {data.valuation.pe}</span>}
            {data.valuation.pb && <span className="ml-2 text-white">PB: {data.valuation.pb}</span>}
            {data.valuation.turnover && <span className="ml-2 text-white">换手: {data.valuation.turnover}%</span>}
            {data.valuation.interpretation && (
              <p className="text-slate-400 mt-1">{data.valuation.interpretation}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TrendJudgmentSection({ data }: { data: TrendJudgment }) {
  const suggestionColors: Record<string, string> = {
    "加仓": "text-emerald-400",
    "减仓": "text-red-400",
    "持有": "text-blue-400",
    "建仓": "text-emerald-400",
    "观望": "text-slate-400",
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
          <span className="text-slate-400 font-medium">{title}</span>
          {content && <p className="text-white mt-1">{content}</p>}
        </div>
      );
    });
  };

  return (
    <div className="border border-slate-700 rounded p-3">
      <h4 className="text-sm font-medium text-slate-300 mb-2">趋势判断</h4>

      <div className="space-y-2">
        {/* Forecast */}
        {data.forecast && (
          <div className="text-sm">
            <span className="text-slate-400">走势预测:</span>
            <div className="mt-1 bg-slate-700/50 rounded p-2">
              {renderParagraphs(data.forecast)}
            </div>
          </div>
        )}

        {/* Suggestion */}
        {data.suggestion && (
          <div className="text-sm">
            <span className="text-slate-400">操作建议:</span>
            <span className={`ml-2 text-lg font-medium ${
              suggestionColors[data.suggestion] || "text-white"
            }`}>
              {data.suggestion}
            </span>
          </div>
        )}

        {/* Reasoning */}
        {data.reasoning && (
          <div className="text-sm bg-slate-700/50 rounded p-2">
            <span className="text-slate-400">理由:</span>
            <div className="mt-1">
              {renderParagraphs(data.reasoning)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
