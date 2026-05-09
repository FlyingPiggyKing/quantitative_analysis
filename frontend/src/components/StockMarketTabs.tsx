"use client";

import { useState, ReactNode } from "react";

interface StockMarketTabsProps {
  aShareContent: ReactNode;
  usContent: ReactNode;
  hkContent?: ReactNode;
  activeTab?: "A" | "US" | "HK";
  onTabChange?: (tab: "A" | "US" | "HK") => void;
  defaultTab?: "A" | "US" | "HK";
}

export default function StockMarketTabs({
  aShareContent,
  usContent,
  hkContent,
  activeTab: controlledActiveTab,
  onTabChange,
  defaultTab = "A"
}: StockMarketTabsProps) {
  const [internalActiveTab, setInternalActiveTab] = useState<"A" | "US" | "HK">(defaultTab);
  const activeTab = controlledActiveTab !== undefined ? controlledActiveTab : internalActiveTab;

  const handleTabChange = (tab: "A" | "US" | "HK") => {
    if (controlledActiveTab !== undefined && onTabChange) {
      onTabChange(tab);
    } else {
      setInternalActiveTab(tab);
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg p-3 sm:p-4">
      {/* Tab Bar */}
      <div className="flex border-b border-slate-700 mb-4">
        <button
          onClick={() => handleTabChange("A")}
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${
            activeTab === "A"
              ? "text-blue-400"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          A股
          {activeTab === "A" && (
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400" />
          )}
        </button>
        <button
          onClick={() => handleTabChange("US")}
          className={`px-4 py-2 text-sm font-medium transition-colors relative ${
            activeTab === "US"
              ? "text-blue-400"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          美股
          {activeTab === "US" && (
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400" />
          )}
        </button>
        {hkContent && (
          <button
            onClick={() => handleTabChange("HK")}
            className={`px-4 py-2 text-sm font-medium transition-colors relative ${
              activeTab === "HK"
                ? "text-blue-400"
                : "text-slate-400 hover:text-slate-300"
            }`}
          >
            港股
            {activeTab === "HK" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400" />
            )}
          </button>
        )}
      </div>

      {/* Tab Content */}
      {activeTab === "A" ? aShareContent : activeTab === "US" ? usContent : hkContent}
    </div>
  );
}
