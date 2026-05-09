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
    <div className="vt-panel p-3 sm:p-4">
      {/* Tab Bar */}
      <div className="flex border-b border-vt-ink-700 mb-4">
        <button
          onClick={() => handleTabChange("A")}
          className={`vt-tab px-4 py-2 transition-colors relative ${
            activeTab === "A" ? "vt-tab-active" : ""
          }`}
        >
          A 股
          {activeTab === "A" && (
            <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
          )}
        </button>
        <button
          onClick={() => handleTabChange("US")}
          className={`vt-tab px-4 py-2 transition-colors relative ${
            activeTab === "US" ? "vt-tab-active" : ""
          }`}
        >
          美 股
          {activeTab === "US" && (
            <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
          )}
        </button>
        {hkContent && (
          <button
            onClick={() => handleTabChange("HK")}
            className={`vt-tab px-4 py-2 transition-colors relative ${
              activeTab === "HK" ? "vt-tab-active" : ""
            }`}
          >
            港 股
            {activeTab === "HK" && (
              <span className="vt-tab-underline absolute bottom-0 left-0 right-0 h-[2px]" />
            )}
          </button>
        )}
      </div>

      {/* Tab Content */}
      {activeTab === "A" ? aShareContent : activeTab === "US" ? usContent : hkContent}
    </div>
  );
}
