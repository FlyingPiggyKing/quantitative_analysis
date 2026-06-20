"use client";

import { useState, useRef, useLayoutEffect } from "react";
import CollapsibleHeader from "@/components/CollapsibleHeader";
import type { CompanyInfo, CompanyLabel, CompanyExecutive } from "@/services/companyInfo";

interface CompanyInfoPanelProps {
  data: CompanyInfo | null;
  loading: boolean;
  error: string | null;
}

const NA = "--";

function formatRegCapital(val: number | null | undefined): string {
  if (val == null) return NA;
  // Tushare returns reg_capital in 万元; convert to 亿元 per project convention.
  return `${(val / 10000).toFixed(2)} 亿元`;
}

function formatEmployees(val: number | null | undefined): string {
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

function CollapsibleText({ value }: { value: string | null | undefined }) {
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
  const [open, setOpen] = useState(true);
  return (
    <section className="vt-panel p-3 sm:p-4">
      <CollapsibleHeader
        title="公 司 信 息"
        open={open}
        onToggle={() => setOpen((o) => !o)}
      />

      {open && (
        <>
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
              {data.market === "A" ? (
                <>
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
                </>
              ) : (
                <HkusPanel data={data} />
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}

/** HK/US layout: mirrors the A-share panel as closely as possible.
 *
 *  The Futu response is a free-form `profile_labels` list (English or
 *  Chinese label names) plus an `executives` list with `position` strings
 *  (English or Chinese). We map that to the A-share fields the panel knows:
 *
 *    公司全称  ← Company Name / 公司名称 / Symbol fallback
 *    法人代表  ← first executive matching chairman-like position
 *    总经理    ← first executive matching CEO/manager-like position
 *    董秘      ← first executive matching secretary-like position
 *    上市日期  ← Listing Date / 上市日期
 *    员工人数  ← Employees / 员工数量
 *    公司主页  ← Website / 网址
 *
 *  The remaining profile_labels that didn't map to a top field go into an
 *  "其他公司信息" (Additional Information) subsection so nothing is lost.
 *  Long descriptions use the same `CollapsibleText` as the A-share branch. */
function HkusPanel({ data }: { data: CompanyInfo }) {
  const labels = (data.profile_labels ?? []).filter((l: CompanyLabel) => l.value);
  const executives: CompanyExecutive[] = (data.executives ?? []).slice(0, 5);

  if (labels.length === 0 && executives.length === 0) {
    return (
      <div className="text-center text-vt-brass-400 text-xs py-3 vt-engraved">
        暂无公司信息
      </div>
    );
  }

  // Build a name -> value map from profile_labels, normalized to uppercase
  // so lookups are case-insensitive regardless of Futu's casing.
  const byName = new Map<string, CompanyLabel>();
  for (const l of labels) {
    byName.set((l.name || "").toUpperCase().trim(), l);
  }
  const pick = (...names: string[]): string | null => {
    for (const n of names) {
      const found = byName.get(n.toUpperCase());
      if (found?.value) return found.value;
    }
    return null;
  };

  // 1. Top-tier fields rendered in the A-share 2-column grid. (Chairman /
  //    manager / secretary are no longer extracted here — the high-level
  //    高管信息 list below already shows the chairman via translatePosition
  //    and merges same-position entries into one row.)
  const comName = pick("公司全称", "公司名称", "COMPANY NAME", "COMPANY NAME (CHINESE)", "COMPANY NAME (ENGLISH)", "SYMBOL");
  const listingDate = pick("上市日期", "LISTING DATE");
  const employees = pick("员工人数", "员工数量", "EMPLOYEES");
  const website = pick("公司网址", "网址", "WEBSITE");
  const city = pick("城市", "CITY");
  const province = pick("省份", "PROVINCE", "STATE");
  const country = pick("国家", "COUNTRY");
  const zip = pick("邮编", "邮政编码", "ZIP", "ZIP CODE");
  const registeredAddr = pick("注册地址", "公司注册地址", "REGISTERED ADDRESS");
  const headOffice = pick("总部办事处及主要营业地点", "总部及主要营业地点", "HEAD OFFICE AND PRINCIPAL PLACE OF BUSINESS", "REGISTERED OFFICE", "OFFICE ADDRESS", "公司地址", "地址", "ADDRESS");
  const mainBusiness = pick("主营业务", "公司业务", "BUSINESS", "MAIN BUSINESS");
  const description = pick("公司简介", "公司介绍", "DESCRIPTION", "INTRODUCTION", "BUSINESS SCOPE");
  const phone = pick("公司电话", "电话", "PHONE");
  const email = pick("公司邮箱", "邮箱", "EMAIL");
  const isin = pick("ISIN 代码", "ISIN", "ISIN代码");
  const issuePrice = pick("发行价", "发行价格", "ISSUE PRICE");
  const founded = pick("成立日期", "FOUNDED");

  // Compose 所在地区 like A-share: "省份 · 城市" (country appended when non-China).
  const region = [province, city].filter(Boolean).join(" · ") ||
    [country, city].filter(Boolean).join(" · ") ||
    null;

  // 2. Build a "consumed" set of label names so we can list the rest below.
  //    The hidden set drops redundant/redundant fields the user has flagged as
  //    not worth showing (symbol is already in the page header, fax / registered
  //    office / head office are either redundant with the page header or with
  //    other fields shown).
  const consumed = new Set([
    "公司全称", "公司名称", "COMPANY NAME", "COMPANY NAME (CHINESE)", "COMPANY NAME (ENGLISH)", "SYMBOL",
    "上市日期", "LISTING DATE",
    "员工人数", "员工数量", "EMPLOYEES",
    "公司网址", "网址", "WEBSITE",
    "城市", "CITY", "省份", "PROVINCE", "STATE", "国家", "COUNTRY", "邮编", "邮政编码", "ZIP", "ZIP CODE",
    "注册地址", "公司注册地址", "REGISTERED ADDRESS",
    "总部办事处及主要营业地点", "总部及主要营业地点", "HEAD OFFICE AND PRINCIPAL PLACE OF BUSINESS", "REGISTERED OFFICE", "OFFICE ADDRESS", "公司地址", "地址", "ADDRESS",
    "主营业务", "公司业务", "BUSINESS", "MAIN BUSINESS",
    "公司简介", "公司介绍", "DESCRIPTION", "INTRODUCTION", "BUSINESS SCOPE",
    "公司电话", "电话", "PHONE",
    "公司邮箱", "邮箱", "EMAIL",
    "ISIN 代码", "ISIN", "ISIN代码",
    "发行价", "发行价格", "ISSUE PRICE",
    "成立日期", "FOUNDED",
    "CEO", "总经理", "CHIEF EXECUTIVE OFFICER", "总裁",
    "董事长", "法定代表人", "CHAIRMAN", "CHAIRMAN NAME",
    "公司秘书", "董秘", "SECRETARY", "BOARD SECRETARY",
  ]);
  const hidden = new Set([
    "公司代码", "SYMBOL",                        // symbol already in page header
    "注册办事处", "REGISTERED OFFICE",            // legal-entity registered agent address
    "总办事处及主要营业地点", "总部办事处及主要营业地点", "总部及主要营业地点",
    "HEAD OFFICE AND PRINCIPAL PLACE OF BUSINESS",  // legal head office — user flagged to hide
    "传真", "FAX",                                // user flagged to hide
  ]);
  const extraLabels = labels.filter(
    (l) => !consumed.has((l.name || "").toUpperCase().trim())
      && !hidden.has((l.name || "").toUpperCase().trim())
  );

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
        <Cell label="公司全称" value={comName ?? NA} />
        <Cell label="上市日期" value={listingDate ?? NA} />
        <Cell label="员工人数" value={employees ? formatEmployees(Number(employees.replace(/[^\d]/g, "")) || null) : NA} />
        <Cell label="ISIN" value={isin ?? NA} />
        {region && <Cell label="所在地区" value={region} />}
        <Cell
          label="公司主页"
          value={
            (() => {
              const site = website;
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

      {extraLabels.length > 0 && (
        <div className="mt-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
            {extraLabels.map((label, idx) => (
              <Cell
                key={`${label.name}-${idx}`}
                label={translateLabel(label.name)}
                value={renderLabelValue(label)}
              />
            ))}
          </div>
        </div>
      )}

      {executives.length > 0 && (() => {
        // Group executives by translated position. The Futu data carries
        // multi-role positions like "INDEPENDENT DIRECTOR, CHAIRMAN OF THE
        // AUDIT COMMITTEE" which translatePosition reduces to a single
        // canonical role (e.g. "独立董事"). Multiple executives sharing the
        // same translated position are merged into one row with names joined
        // by "、" — this collapses the typical 4-5 独立董事 rows into one.
        const grouped = new Map<string, string[]>();
        for (const exec of executives) {
          const who = exec.displayName || exec.name;
          if (!who) continue;
          const pos = translatePosition(exec.position);
          if (!pos || pos === "—") continue;
          if (!grouped.has(pos)) grouped.set(pos, []);
          grouped.get(pos)!.push(who);
        }
        if (grouped.size === 0) return null;
        return (
          <div className="mt-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1">
              {[...grouped.entries()].map(([pos, names]) => (
                <ExecRow
                  key={pos}
                  position={pos}
                  names={names}
                />
              ))}
            </div>
          </div>
        );
      })()}

      {mainBusiness && (
        <div className="mt-4">
          <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-1">
            主要业务及产品
          </div>
          <CollapsibleText value={mainBusiness} />
        </div>
      )}

      {description && description !== mainBusiness && (
        <div className="mt-4">
          <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-1">
            公司介绍
          </div>
          <CollapsibleText value={description} />
        </div>
      )}
    </div>
  );
}

/** Translate a Futu English position string to a concise Chinese label. Falls
 *  back to a 40-char preview of the first comma-separated chunk if no
 *  pattern matches. Used for the 高管信息 list — same-position entries
 *  are merged into one row. */
function translatePosition(pos: string | null | undefined): string {
  if (!pos) return "—";
  const s = pos.toUpperCase();
  if (/CHAIRMAN.*BOARD|CHAIRMAN OF/.test(s) || /董事长/.test(pos)) return "董事长";
  if (/VICE\s*CHAIRMAN|副主席|副董事长/.test(s)) return "副董事长";
  if (/CHIEF\s*EXECUTIVE\b|\bCEO\b|总裁|行政总裁/.test(s)) return "总经理";
  if (/CHIEF\s*FINANCIAL\b|\bCFO\b|财务总监/.test(s)) return "财务总监";
  if (/CHIEF\s*OPERATING\b|\bCOO\b|运营总监/.test(s)) return "运营总监";
  if (/CHIEF\s*TECHNOLOGY\b|\bCTO\b|技术总监/.test(s)) return "技术总监";
  if (/CHIEF\s*MARKETING\b|\bCMO\b|市场总监/.test(s)) return "市场总监";
  if (/CHIEF\s*HUMAN\s*RESOURCES\b|\bCHRO\b|人力总监/.test(s)) return "人力总监";
  if (/CHIEF\s*ACCOUNTING\b|会计主管|财务主管/.test(s)) return "会计主管";
  if (/EXECUTIVE\s*VICE\s*PRESIDENT|\bEVP\b|执行副总裁/.test(s)) return "执行副总裁";
  if (/CORPORATE\s*VICE\s*PRESIDENT|\bCVP\b|副总裁/.test(s)) return "副总裁";
  if (/EXECUTIVE\s*DIRECTOR|执行董事/.test(s)) return "执行董事";
  if (/NON[\s-]*EXECUTIVE\s*DIRECTOR|非执行董事/.test(s)) return "非执行董事";
  if (/INDEPENDENT\s*NON[\s-]*EXECUTIVE\s*DIRECTOR|独立非执行董事/.test(s)) return "独立非执行董事";
  if (/INDEPENDENT\s*DIRECTOR|独立董事/.test(s)) return "独立董事";
  if (/SECRETARY|公司秘书|DIRECTOR.*SECRETARY|董秘/.test(s)) return "董秘";
  if (/PRESIDENT\b|总裁|主席/.test(s)) return "总裁";
  // Fallback: show the first comma-separated chunk, capped at 40 chars.
  const first = pos.split(/[;,]/)[0].trim();
  return first.length > 40 ? first.slice(0, 37) + "…" : first;
}

/** Render one executive entry in the 高管信息 list. Position goes on top as
 *  a small uppercase caption (can wrap freely); names sit below as the
 *  prominent value. For merged entries, names are joined by "、". This
 *  layout avoids the side-by-side Cell getting squashed by very long
 *  English position strings (e.g. "EXECUTIVE VICE PRESIDENT AND CHIEF
 *  HUMAN RESOURCES OFFICER") for US stocks. */
function ExecRow({ position, names }: { position: string; names: string[] }) {
  return (
    <div className="py-1.5 border-b border-vt-ink-700/40">
      <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-0.5 break-words">
        {position}
      </div>
      <div className="font-[var(--font-geist-mono)] text-xs text-vt-parchment break-words leading-relaxed">
        {names.join("、")}
      </div>
    </div>
  );
}

/** Translation table for common Futu English label names. The Futu
 *  ``get_company_profile`` API only returns English labels; this map gives
 *  a Chinese display name for the most common ones so the panel matches the
 *  A-share panel's language. Unmapped labels fall through to the English
 *  name unchanged. Keep keys ALL CAPS to match Futu's casing. */
const LABEL_TRANSLATIONS: Record<string, string> = {
  SYMBOL: "股票代码",
  "COMPANY NAME": "公司全称",
  "COMPANY NAME (CHINESE)": "公司中文名",
  "COMPANY NAME (ENGLISH)": "公司英文名",
  ISIN: "ISIN 代码",
  "LISTING DATE": "上市日期",
  "ISSUE PRICE": "发行价",
  "SHARES OFFERED": "发行股数",
  FOUNDED: "成立日期",
  "REGISTERED ADDRESS": "注册地址",
  "AUDIT INSTITUTION": "核数师",
  "COMPANY CATEGORY": "公司类别",
  "REGISTERED OFFICE": "注册办事处",
  "HEAD OFFICE AND PRINCIPAL PLACE OF BUSINESS": "总部及主要营业地点",
  "FISCAL YEAR ENDS": "财政年度截止",
  EMPLOYEES: "员工人数",
  MARKET: "市场",
  PHONE: "公司电话",
  FAX: "公司传真",
  EMAIL: "公司邮箱",
  WEBSITE: "公司网址",
  BUSINESS: "主营业务",
  DESCRIPTION: "公司简介",
  "CHAIRMAN NAME": "董事长",
  "BOARD LOT": "每手股数",
  "PAR VALUE": "票面值",
  "BUSINESS SCOPE": "经营范围",
  "INTRODUCTION": "公司简介",
  "INDUSTRY": "所属行业",
  "REGION": "所在地区",
  ADDRESS: "公司地址",
  "OFFICE ADDRESS": "办公地址",
};

function translateLabel(name: string): string {
  return LABEL_TRANSLATIONS[name?.toUpperCase()] ?? name;
}

function renderLabelValue(label: CompanyLabel) {
  if (!label.value) return NA;
  if (label.fieldType === 1) {
    const href = label.value.startsWith("http") ? label.value : `https://${label.value}`;
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-vt-brass-300 hover:text-vt-brass-400 underline-offset-2 hover:underline"
      >
        {label.value}
      </a>
    );
  }
  return label.value;
}
