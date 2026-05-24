"use client";

import { useState, ReactNode } from "react";

type ModuleType = "watchlist" | "analysis";

interface ModuleTabsProps {
  watchlistContent: ReactNode;
  analysisContent: ReactNode;
  activeModule?: ModuleType;
  onModuleChange?: (module: ModuleType) => void;
  defaultModule?: ModuleType;
}

export default function ModuleTabs({
  watchlistContent,
  analysisContent,
  activeModule: controlledActiveModule,
  onModuleChange,
  defaultModule = "watchlist"
}: ModuleTabsProps) {
  const [internalActiveModule, setInternalActiveModule] = useState<ModuleType>(defaultModule);
  const activeModule = controlledActiveModule !== undefined ? controlledActiveModule : internalActiveModule;

  const handleModuleChange = (module: ModuleType) => {
    if (controlledActiveModule !== undefined && onModuleChange) {
      onModuleChange(module);
    } else {
      setInternalActiveModule(module);
    }
  };

  return (
    <div className="vt-panel p-3 sm:p-4">
      {/* Tab Bar */}
      <div className="flex border-b border-vt-ink-700 mb-4">
        <button
          onClick={() => handleModuleChange("watchlist")}
          className={`vt-tab px-4 py-2 transition-colors relative text-base font-semibold ${
            activeModule === "watchlist" ? "vt-tab-active" : ""
          }`}
        >
          我 的 自 选
          {activeModule === "watchlist" && (
            <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
          )}
        </button>
        <button
          onClick={() => handleModuleChange("analysis")}
          className={`vt-tab px-4 py-2 transition-colors relative text-base font-semibold ${
            activeModule === "analysis" ? "vt-tab-active" : ""
          }`}
        >
          投 资 分 析
          {activeModule === "analysis" && (
            <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
          )}
        </button>
      </div>

      {/* Tab Content */}
      {activeModule === "watchlist" ? watchlistContent : analysisContent}
    </div>
  );
}
