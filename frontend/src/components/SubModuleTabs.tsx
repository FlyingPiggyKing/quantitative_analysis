"use client";

import { useState, ReactNode, useEffect } from "react";

type WatchlistSubModule = "A" | "US" | "HK";
type AnalysisSubModule = "dragonTiger";
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
    return activeModule === "watchlist" ? "A" : "dragonTiger";
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
    const defaultSub = newModule === "watchlist" ? "A" : "dragonTiger";
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

    return (
      <div>
        {/* Tab Bar with date on right */}
        <div className="flex items-center justify-between border-b border-vt-ink-700 mb-4">
          <button
            className={`vt-tab px-4 py-2 transition-colors relative text-base font-semibold`}
          >
            机 构 龙 虎 榜
            <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
          </button>
          {dragonTigerDate && (
            <span className="vt-engraved text-xs mr-2">{dragonTigerDate}</span>
          )}
        </div>

        {/* Sub-module Content - DragonTigerList without its own header */}
        <div>
          {analysisSubContent.renderDragonTigerContent((date) => setDragonTigerDate(date))}
        </div>
      </div>
    );
  }

  return null;
}
