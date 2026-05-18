"use client";

import { useState } from "react";

interface InstitutionalPrediction {
  symbol: string;
  name: string;
  trend_direction: "up" | "down" | "neutral";
  confidence: number;
  summary: string;
  analyzed_at: string;
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

interface InstitutionalAnalysisPanelProps {
  prediction: InstitutionalPrediction;
}

const cardStyle = {
  background: "rgba(40,32,22,0.6)",
  border: "1px solid rgba(120,95,50,0.2)",
};

export default function InstitutionalAnalysisPanel({ prediction }: InstitutionalAnalysisPanelProps) {
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});

  const toggleSection = (key: string) => {
    setCollapsedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const sections = [
    { key: "macro", title: "一、宏观产业周期", data: prediction.宏观产业周期 },
    { key: "sector", title: "二、板块行业景气", data: prediction.板块行业景气 },
    { key: "fundamental", title: "三、公司基本面质变", data: prediction.公司基本面质变 },
    { key: "capital", title: "四、资金筹码结构", data: prediction.资金筹码结构 },
    { key: "technical", title: "五、技术形态量价", data: prediction.技术形态量价 },
    { key: "wave", title: "六、波段操作执行", data: prediction.波段操作执行 },
    { key: "judgment", title: "综合判断", data: prediction.综合判断 },
  ].filter(s => s.data);

  if (sections.length === 0) {
    return (
      <div className="vt-engraved py-2">
        <p>暂无详细分析数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sections.map(({ key, title, data }) => (
        <CollapsibleSection
          key={key}
          title={title}
          isCollapsed={!!collapsedSections[key]}
          onToggle={() => toggleSection(key)}
        >
          <SectionContent sectionKey={key} data={data} />
        </CollapsibleSection>
      ))}

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
    <div>
      <button
        onClick={onToggle}
        className="w-full flex justify-between items-center p-3 min-h-[44px] active:opacity-80"
      >
        <span className="font-[var(--font-playfair)] tracking-[0.16em] uppercase text-vt-brass-400 text-sm">{title}</span>
        <span className="text-vt-brass-400 text-xl font-[var(--font-playfair)]">{isCollapsed ? "+" : "−"}</span>
      </button>
      <div className={`${isCollapsed ? "hidden" : "block"}`}>
        {children}
      </div>
    </div>
  );
}

function SectionContent({ sectionKey, data }: { sectionKey: string; data: any }) {
  if (!data) return null;

  switch (sectionKey) {
    case "macro":
      return <MacroCycleSection data={data} />;
    case "sector":
      return <SectorProsperitySection data={data} />;
    case "fundamental":
      return <FundamentalChangeSection data={data} />;
    case "capital":
      return <CapitalStructureSection data={data} />;
    case "technical":
      return <TechnicalPatternSection data={data} />;
    case "wave":
      return <WaveExecutionSection data={data} />;
    case "judgment":
      return <ComprehensiveJudgmentSection data={data} />;
    default:
      return null;
  }
}

function MacroCycleSection({ data }: { data: InstitutionalPrediction["宏观产业周期"] }) {
  if (!data) return null;
  return (
    <div className="space-y-2 pt-1 pb-2">
      {data.macro_summary && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">宏观概述:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.macro_summary}</p>
        </div>
      )}
      {data.industry_cycle && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">行业周期:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.industry_cycle}</p>
        </div>
      )}
      {data.policy_impact && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">政策影响:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.policy_impact}</p>
        </div>
      )}
    </div>
  );
}

function SectorProsperitySection({ data }: { data: InstitutionalPrediction["板块行业景气"] }) {
  if (!data) return null;
  return (
    <div className="space-y-2 pt-1 pb-2">
      {data.sector_momentum && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">板块动量:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.sector_momentum}</p>
        </div>
      )}
      {data.prosperity_trend && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">景气趋势:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.prosperity_trend}</p>
        </div>
      )}
      {data.leading_stocks && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">龙头个股:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.leading_stocks}</p>
        </div>
      )}
    </div>
  );
}

function FundamentalChangeSection({ data }: { data: InstitutionalPrediction["公司基本面质变"] }) {
  if (!data) return null;
  return (
    <div className="space-y-2 pt-1 pb-2">
      {data.business_change && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">业务质变:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.business_change}</p>
        </div>
      )}
      {data.recent_events && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">近期事项:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.recent_events}</p>
        </div>
      )}
      {data.fundamental_assessment && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">基本面评价:</span>
          <p className={`mt-1 leading-relaxed font-[var(--font-playfair)] ${
            data.fundamental_assessment.includes("优") ? "text-vt-oxblood-400" :
            data.fundamental_assessment.includes("良") ? "text-vt-brass-300" : "text-vt-parchment"
          }`}>{data.fundamental_assessment}</p>
        </div>
      )}
    </div>
  );
}

function CapitalStructureSection({ data }: { data: InstitutionalPrediction["资金筹码结构"] }) {
  if (!data) return null;
  return (
    <div className="space-y-2 pt-1 pb-2">
      {data.dragon_tiger_net && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">龙虎榜净买卖:</span>
          <span className={`ml-2 font-[var(--font-geist-mono)] text-vt-parchment ${
            data.dragon_tiger_net.startsWith("+") ? "text-vt-oxblood-400" : "text-vt-emerald-400"
          }`}>{data.dragon_tiger_net}</span>
        </div>
      )}
      {data.institutional_strength && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">机构力道:</span>
          <span className={`ml-2 font-[var(--font-playfair)] ${
            data.institutional_strength.includes("偏多") || data.institutional_strength.includes("看多") ? "text-vt-oxblood-400" :
            data.institutional_strength.includes("偏空") || data.institutional_strength.includes("看空") ? "text-vt-emerald-400" : "text-vt-parchment"
          }`}>{data.institutional_strength}</span>
        </div>
      )}
      {data.main_force_flow && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">主力资金:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.main_force_flow}</p>
        </div>
      )}
      {data.seat_distribution && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">席位分布:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.seat_distribution}</p>
        </div>
      )}
      {data.retail_vs_institutional && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">散户vs机构:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.retail_vs_institutional}</p>
        </div>
      )}
    </div>
  );
}

function TechnicalPatternSection({ data }: { data: InstitutionalPrediction["技术形态量价"] }) {
  if (!data) return null;
  return (
    <div className="space-y-2 pt-1 pb-2">
      {data.kline_pattern && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">K线形态:</span>
          <span className="ml-2 text-vt-parchment">{data.kline_pattern}</span>
        </div>
      )}
      <div className="grid grid-cols-2 gap-2 text-xs">
        {data.macd && (
          <div className="rounded p-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">MACD:</span>
            <span className="ml-1 text-vt-parchment font-[var(--font-geist-mono)]">{data.macd.value}</span>
            <span className={`ml-2 font-[var(--font-playfair)] ${
              data.macd.signal?.includes("金叉") ? "text-vt-oxblood-400" : "text-vt-emerald-400"
            }`}>{data.macd.signal}</span>
            {data.macd.interpretation && (
              <p className="text-vt-parchment-soft mt-1">{data.macd.interpretation}</p>
            )}
          </div>
        )}
        {data.rsi && (
          <div className="rounded p-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">RSI:</span>
            <span className="ml-1 text-vt-parchment font-[var(--font-geist-mono)]">{data.rsi.value}</span>
            <span className={`ml-2 font-[var(--font-playfair)] ${
              data.rsi.zone?.includes("超买") ? "text-vt-oxblood-400" :
              data.rsi.zone?.includes("超卖") ? "text-vt-emerald-400" : "text-vt-parchment-dim"
            }`}>{data.rsi.zone}</span>
            {data.rsi.interpretation && (
              <p className="text-vt-parchment-soft mt-1">{data.rsi.interpretation}</p>
            )}
          </div>
        )}
        {data.ma && (
          <div className="rounded p-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">均线:</span>
            <span className="ml-1 text-vt-parchment">{data.ma.position}</span>
            {data.ma.interpretation && (
              <p className="text-vt-parchment-soft mt-1">{data.ma.interpretation}</p>
            )}
          </div>
        )}
        {data.volume && (
          <div className="rounded p-2" style={cardStyle}>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">成交量:</span>
            <span className="ml-1 text-vt-parchment font-[var(--font-geist-mono)]">{(Number(data.volume.ratio) || 0).toFixed(2)}</span>
            {data.volume.interpretation && (
              <p className="text-vt-parchment-soft mt-1">{data.volume.interpretation}</p>
            )}
          </div>
        )}
      </div>
      {data.valuation && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">估值:</span>
          <span className="ml-2 text-vt-parchment font-[var(--font-geist-mono)]">
            PE: {data.valuation.pe} | PB: {data.valuation.pb} | 换手: {data.valuation.turnover} | 市值: {data.valuation.market_cap}
          </span>
          {data.valuation.interpretation && (
            <p className="text-vt-parchment-soft mt-1">{data.valuation.interpretation}</p>
          )}
        </div>
      )}
    </div>
  );
}

function WaveExecutionSection({ data }: { data: InstitutionalPrediction["波段操作执行"] }) {
  if (!data) return null;
  return (
    <div className="space-y-3 pt-1 pb-2">
      {data.第一轮短线 && (
        <WaveCard wave={data.第一轮短线} label="第一轮（短线 5-20天）" />
      )}
      {data.第二轮中线 && (
        <WaveCard wave={data.第二轮中线} label="第二轮（中线 20-60天）" />
      )}
    </div>
  );
}

function WaveCard({ wave, label }: { wave: any; label: string }) {
  const directionColors: Record<string, string> = {
    "看多": "text-vt-oxblood-400",
    "看空": "text-vt-emerald-400",
    "震荡": "text-vt-brass-300",
  };
  const colorClass = directionColors[wave.direction] || "text-vt-parchment";

  return (
    <div className="rounded p-3 text-sm" style={cardStyle}>
      <div className="flex items-center justify-between mb-2">
        <span className="vt-engraved not-italic text-xs uppercase tracking-wider">{label}</span>
        <span className={`font-[var(--font-playfair)] text-lg font-bold ${colorClass}`}>{wave.direction}</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <div><span className="vt-parchment-dim">时间:</span> <span className="text-vt-parchment">{wave.timeframe}</span></div>
        <div><span className="vt-parchment-dim">入场:</span> <span className="text-vt-parchment">{wave.entry_price}</span></div>
        <div><span className="vt-parchment-dim">止损:</span> <span className="text-vt-emerald-400">{wave.stop_loss}</span></div>
        <div><span className="vt-parchment-dim">目标:</span> <span className="text-vt-oxblood-400">{wave.target_price}</span></div>
        <div className="col-span-2"><span className="vt-parchment-dim">风险收益:</span> <span className="text-vt-parchment">{wave.risk_reward}</span></div>
      </div>
    </div>
  );
}

function ComprehensiveJudgmentSection({ data }: { data: InstitutionalPrediction["综合判断"] }) {
  if (!data) return null;

  const tierColors: Record<string, string> = {
    "短线机会": "text-vt-oxblood-400",
    "中线机会": "text-vt-oxblood-400",
    "长线机会": "text-vt-brass-300",
    "观望": "text-vt-parchment-dim",
  };

  return (
    <div className="space-y-2 pt-1 pb-2">
      {data.short_term_outlook && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">短期展望（5-20天）:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.short_term_outlook}</p>
        </div>
      )}
      {data.medium_term_outlook && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">中期展望（20-60天）:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.medium_term_outlook}</p>
        </div>
      )}
      {data.investment_tier && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">投资评级:</span>
          <span className={`ml-2 font-[var(--font-playfair)] text-lg font-bold ${tierColors[data.investment_tier] || "text-vt-parchment"}`}>
            {data.investment_tier}
          </span>
        </div>
      )}
      {data.key_risks && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">主要风险:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.key_risks}</p>
        </div>
      )}
      {data.reasoning && (
        <div className="rounded p-3 text-sm" style={cardStyle}>
          <span className="vt-engraved not-italic text-xs uppercase tracking-wider">综合逻辑:</span>
          <p className="text-vt-parchment mt-1 leading-relaxed">{data.reasoning}</p>
        </div>
      )}
    </div>
  );
}
