"use client";

import { useState, ReactNode, useEffect } from "react";

type WatchlistSubModule = "A" | "US" | "HK";
type AnalysisSubModule = "dragonTiger" | "moneyFlow" | "indexMetrics";
type SubModuleType = WatchlistSubModule | AnalysisSubModule;

interface SubModuleTabsProps {
  activeModule: "watchlist" | "analysis";
  watchlistSubContent?: {
    aContent: ReactNode;
    usContent: ReactNode;
    hkContent?: ReactNode;
  };
  analysisSubContent?: {
    renderDragonTigerContent: (onDateChange: (date: string) => void) => ReactNode;
    renderMoneyFlowContent: () => ReactNode;
    renderIndexMetricsContent?: () => ReactNode;
  };
  activeSubModule?: SubModuleType;
  onSubModuleChange?: (subModule: SubModuleType) => void;
}

export default function SubModuleTabs({
  activeModule,
  watchlistSubContent,
  analysisSubContent,
  activeSubModule: controlledActiveSubModule,
  onSubModuleChange,
}: SubModuleTabsProps) {
  const getDefaultSubModule = (): SubModuleType => {
    return activeModule === "watchlist" ? "A" : "indexMetrics";
  };

  const [internalActiveSubModule, setInternalActiveSubModule] = useState<SubModuleType>(getDefaultSubModule);
  const activeSubModule = controlledActiveSubModule !== undefined ? controlledActiveSubModule : internalActiveSubModule;

  const handleSubModuleChange = (subModule: SubModuleType) => {
    if (controlledActiveSubModule !== undefined && onSubModuleChange) {
      onSubModuleChange(subModule);
    } else {
      setInternalActiveSubModule(subModule);
    }
  };

  // When module changes, reset sub-module to default
  const handleModuleChange = (newModule: "watchlist" | "analysis") => {
    const defaultSub = newModule === "watchlist" ? "A" : "indexMetrics";
    setInternalActiveSubModule(defaultSub);
    if (onSubModuleChange) {
      onSubModuleChange(defaultSub);
    }
  };

  if (activeModule === "watchlist" && watchlistSubContent) {
    return (
      <div>
        {/* Bottom Tab Bar */}
        <div className="flex border-b border-vt-ink-700 mt-4">
          <button
            onClick={() => handleSubModuleChange("A")}
            className={`vt-tab px-4 py-2 transition-colors relative ${
              activeSubModule === "A" ? "vt-tab-active" : ""
            }`}
          >
            A 股
            {activeSubModule === "A" && (
              <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
            )}
          </button>
          <button
            onClick={() => handleSubModuleChange("US")}
            className={`vt-tab px-4 py-2 transition-colors relative ${
              activeSubModule === "US" ? "vt-tab-active" : ""
            }`}
          >
            美 股
            {activeSubModule === "US" && (
              <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
            )}
          </button>
          {watchlistSubContent.hkContent && (
            <button
              onClick={() => handleSubModuleChange("HK")}
              className={`vt-tab px-4 py-2 transition-colors relative ${
                activeSubModule === "HK" ? "vt-tab-active" : ""
              }`}
            >
              港 股
              {activeSubModule === "HK" && (
                <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
              )}
            </button>
          )}
        </div>

        {/* Sub-module Content */}
        <div className="mt-4">
          {activeSubModule === "A" ? watchlistSubContent.aContent :
           activeSubModule === "US" ? watchlistSubContent.usContent :
           watchlistSubContent.hkContent}
        </div>
      </div>
    );
  }

  if (activeModule === "analysis" && analysisSubContent) {
    const [dragonTigerDate, setDragonTigerDate] = useState<string>("");
    const [moneyFlowDate, setMoneyFlowDate] = useState<string>("");

    return (
      <div>
        {/* Tab Bar with horizontal scroll on mobile */}
        <div className="flex items-center border-b border-vt-ink-700 mb-4">
          <div className="flex flex-1 overflow-x-auto scrollbar-hide">
            {analysisSubContent.renderIndexMetricsContent && (
              <button
                onClick={() => handleSubModuleChange("indexMetrics")}
                className={`vt-tab px-4 py-2 transition-colors relative text-base font-semibold whitespace-nowrap shrink-0 ${
                  activeSubModule === "indexMetrics" ? "vt-tab-active" : ""
                }`}
              >
                指 数 指 标
                {activeSubModule === "indexMetrics" && (
                  <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
                )}
              </button>
            )}
            <button
              onClick={() => handleSubModuleChange("moneyFlow")}
              className={`vt-tab px-4 py-2 transition-colors relative text-base font-semibold whitespace-nowrap shrink-0 ${
                activeSubModule === "moneyFlow" ? "vt-tab-active" : ""
              }`}
            >
              资 金 流 向
              {activeSubModule === "moneyFlow" && (
                <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
              )}
            </button>
            <button
              onClick={() => handleSubModuleChange("dragonTiger")}
              className={`vt-tab px-4 py-2 transition-colors relative text-base font-semibold whitespace-nowrap shrink-0 ${
                activeSubModule === "dragonTiger" ? "vt-tab-active" : ""
              }`}
            >
              机 构 龙 虎 榜
              {activeSubModule === "dragonTiger" && (
                <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
              )}
            </button>
          </div>
          {(dragonTigerDate || moneyFlowDate) && (
            <span className="vt-engraved text-xs mr-2 shrink-0">
              {activeSubModule === "dragonTiger" ? dragonTigerDate : moneyFlowDate}
            </span>
          )}
        </div>

        {/* Sub-module Content */}
        <div>
          {activeSubModule === "dragonTiger" ? (
            analysisSubContent.renderDragonTigerContent((date) => setDragonTigerDate(date))
          ) : activeSubModule === "moneyFlow" ? (
            analysisSubContent.renderMoneyFlowContent()
          ) : activeSubModule === "indexMetrics" && analysisSubContent.renderIndexMetricsContent ? (
            analysisSubContent.renderIndexMetricsContent()
          ) : null}
        </div>
      </div>
    );
  }

  return null;
}
