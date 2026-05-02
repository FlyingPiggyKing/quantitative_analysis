"use client";

import { useState, ReactNode } from "react";

interface StockMarketTabsProps {
  aShareContent: ReactNode;
  usContent: ReactNode;
  defaultTab?: "A" | "US";
}

export default function StockMarketTabs({
  aShareContent,
  usContent,
  defaultTab = "A"
}: StockMarketTabsProps) {
  const [activeTab, setActiveTab] = useState<"A" | "US">(defaultTab);

  return (
    <div className="bg-slate-800 rounded-lg p-3 sm:p-4">
      {/* Tab Bar */}
      <div className="flex border-b border-slate-700 mb-4">
        <button
          onClick={() => setActiveTab("A")}
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
          onClick={() => setActiveTab("US")}
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
      </div>

      {/* Tab Content */}
      {activeTab === "A" ? aShareContent : usContent}
    </div>
  );
}
