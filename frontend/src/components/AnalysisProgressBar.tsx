"use client";

import { TaskStatusResponse } from "@/services/trendPrediction";

interface AnalysisProgressBarProps {
  progress: TaskStatusResponse | null;
  onDismiss: () => void;
  onClearTask: () => void;
}

export default function AnalysisProgressBar({ progress, onDismiss, onClearTask }: AnalysisProgressBarProps) {
  if (!progress) {
    return null;
  }

  const { current, total, status } = progress;
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50">
      <div
        className="border-t-2"
        style={{
          background:
            "linear-gradient(180deg, rgba(28,22,15,0.97) 0%, rgba(14,11,7,0.98) 100%)",
          borderTopColor: "var(--vt-brass-600)",
          boxShadow:
            "0 -1px 0 rgba(241,214,138,0.18), 0 -8px 24px rgba(0,0,0,0.6)",
        }}
      >
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm">
              <span className="vt-pred-col-header mr-2">Analyzing</span>
              <span className="text-vt-parchment font-[var(--font-geist-mono)]">{current}/{total}</span>
              <span className="text-vt-parchment-dim ml-1">stocks</span>
              <span className="text-vt-brass-300 ml-2 font-[var(--font-geist-mono)]">({percentage}%)</span>
              {status === "running" && <span className="ml-3 vt-engraved not-italic text-vt-brass-300 tracking-widest text-xs uppercase">Running…</span>}
              {status === "completed" && <span className="ml-3 vt-engraved not-italic text-vt-emerald-400 tracking-widest text-xs uppercase">Completed</span>}
              {status === "failed" && <span className="ml-3 vt-engraved not-italic text-vt-oxblood-400 tracking-widest text-xs uppercase">Failed</span>}
            </div>
            <div className="flex items-center gap-2">
              {(status === "failed" || status === "completed") && (
                <button
                  onClick={onClearTask}
                  className="vt-btn-secondary px-3 py-1 text-xs"
                  style={{ color: "var(--vt-oxblood-400)" }}
                >
                  清 除 任 务
                </button>
              )}
              <button
                onClick={onDismiss}
                className="text-vt-parchment-dim hover:text-vt-brass-300 transition-colors p-1"
                aria-label="Dismiss progress"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
          <div
            className="w-full h-2 overflow-hidden rounded-sm"
            style={{
              background: "linear-gradient(180deg, #0a0805 0%, #14110d 100%)",
              boxShadow:
                "inset 0 2px 4px rgba(0,0,0,0.7), inset 0 -1px 0 rgba(241,214,138,0.06)",
              border: "1px solid var(--vt-ink-700)",
            }}
          >
            <div
              className="h-full transition-all duration-300 ease-out"
              style={{
                width: `${percentage}%`,
                background:
                  status === "failed"
                    ? "linear-gradient(180deg, #d6705c 0%, #a8392a 60%, #7a2618 100%)"
                    : "linear-gradient(180deg, #f3d680 0%, #d8ad48 45%, #a87b1f 100%)",
                boxShadow:
                  status === "failed"
                    ? "0 0 10px rgba(199,90,74,0.5), inset 0 1px 0 rgba(255,200,180,0.4)"
                    : "0 0 12px rgba(229,193,99,0.55), inset 0 1px 0 rgba(255,240,195,0.5)",
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
