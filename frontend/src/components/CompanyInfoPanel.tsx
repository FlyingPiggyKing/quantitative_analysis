"use client";

import { useState, useRef, useLayoutEffect } from "react";
import type { CompanyInfo } from "@/services/companyInfo";

interface CompanyInfoPanelProps {
  data: CompanyInfo | null;
  loading: boolean;
  error: string | null;
}

const NA = "--";

function formatRegCapital(val: number | null): string {
  if (val == null) return NA;
  // Tushare returns reg_capital in 万元; convert to 亿元 per project convention.
  return `${(val / 10000).toFixed(2)} 亿元`;
}

function formatEmployees(val: number | null): string {
  if (val == null) return NA;
  return val.toLocaleString("zh-CN");
}

/** Split a possibly-semicolon-separated list (Tushare occasionally returns
 *  "site1;site2" for website/email/office) and return the first non-empty entry. */
function firstOf(value: string | null | undefined): string | null {
  if (!value) return null;
  const parts = value.split(/[;；]/).map((s) => s.trim()).filter(Boolean);
  return parts[0] ?? null;
}

function CollapsibleText({ value }: { value: string | null }) {
  const [expanded, setExpanded] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const ref = useRef<HTMLParagraphElement | null>(null);

  // Measure whether the clamped text actually overflows. We compare:
  //   scrollHeight = natural (unclamped) height
  //   clientHeight = visible (clamped) height
  // The element starts clamped; the browser reports both honestly.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setOverflows(el.scrollHeight - el.clientHeight > 1);
  }, [value]);

  if (!value) return <span className="text-vt-parchment-dim">--</span>;
  const clampStyle: React.CSSProperties = expanded
    ? {}
    : {
        display: "-webkit-box",
        WebkitLineClamp: 3,
        WebkitBoxOrient: "vertical",
        overflow: "hidden",
      };
  return (
    <div>
      <p
        ref={ref}
        style={clampStyle}
        className="whitespace-pre-wrap font-[var(--font-geist-mono)] text-xs text-vt-parchment leading-relaxed"
      >
        {value}
      </p>
      {overflows && (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
          className="mt-1 inline-block text-xs text-vt-brass-300 hover:text-vt-brass-400 cursor-pointer select-none"
        >
          [{expanded ? "收起" : "展开"}]
        </button>
      )}
    </div>
  );
}

function Cell({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-baseline gap-3 py-1 border-b border-vt-ink-700/40">
      <span className="vt-engraved not-italic text-[10px] tracking-widest uppercase whitespace-nowrap text-vt-parchment-dim">
        {label}
      </span>
      <span className="font-[var(--font-geist-mono)] text-xs text-vt-parchment text-right break-all">
        {value}
      </span>
    </div>
  );
}

export default function CompanyInfoPanel({
  data,
  loading,
  error,
}: CompanyInfoPanelProps) {
  return (
    <section className="vt-panel p-3 sm:p-4">
      <h2 className="font-[var(--font-playfair)] text-lg tracking-[0.18em] text-vt-parchment uppercase mb-4">
        <span className="text-vt-brass-400">❖</span> 公 司 信 息
      </h2>

      {loading && (
        <div className="animate-pulse space-y-2">
          <div className="h-3 bg-vt-ink-700 rounded w-1/3" />
          <div className="h-3 bg-vt-ink-700 rounded w-1/2" />
          <div className="h-3 bg-vt-ink-700 rounded w-2/3" />
          <div className="h-3 bg-vt-ink-700 rounded w-1/2" />
          <div className="h-3 bg-vt-ink-700 rounded w-3/5" />
          <div className="h-3 bg-vt-ink-700 rounded w-1/2" />
        </div>
      )}

      {!loading && (error || !data) && (
        <div className="text-center text-vt-brass-400 text-xs py-3 vt-engraved">
          {error || "暂无公司信息"}
        </div>
      )}

      {!loading && data && (
        <div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
            <Cell label="公司全称" value={data.com_name ?? NA} />
            <Cell label="法人代表" value={data.chairman ?? NA} />
            <Cell label="总经理" value={data.manager ?? NA} />
            <Cell label="董秘" value={data.secretary ?? NA} />
            <Cell label="注册资本" value={formatRegCapital(data.reg_capital)} />
            <Cell label="注册日期" value={data.setup_date ?? NA} />
            <Cell
              label="所在地区"
              value={[data.province, data.city].filter(Boolean).join(" · ") || NA}
            />
            <Cell label="员工人数" value={formatEmployees(data.employees)} />
            <Cell
              label="公司主页"
              value={
                (() => {
                  const site = firstOf(data.website);
                  if (!site) return NA;
                  const href = site.startsWith("http") ? site : `https://${site}`;
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-vt-brass-300 hover:text-vt-brass-400 underline-offset-2 hover:underline"
                    >
                      {site}
                    </a>
                  );
                })()
              }
            />
          </div>

          <div className="mt-4">
            <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-1">
              办公地址
            </div>
            <p className="font-[var(--font-geist-mono)] text-xs text-vt-parchment leading-relaxed">
              {data.office ?? NA}
            </p>
          </div>

          <div className="mt-4">
            <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-1">
              主要业务及产品
            </div>
            <CollapsibleText value={data.main_business} />
          </div>

          <div className="mt-4">
            <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-1">
              经营范围
            </div>
            <CollapsibleText value={data.business_scope} />
          </div>

          <div className="mt-4">
            <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-1">
              公司介绍
            </div>
            <CollapsibleText value={data.introduction} />
          </div>
        </div>
      )}
    </section>
  );
}
