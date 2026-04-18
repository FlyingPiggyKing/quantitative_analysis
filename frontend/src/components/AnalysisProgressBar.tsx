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
    <div className="fixed bottom-0 left-0 right-0 bg-gray-100 border-t border-gray-300 z-50">
      <div className="max-w-4xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-gray-700 text-sm">
            <span className="font-medium">Analyzing: </span>
            <span>{current}/{total} stocks ({percentage}%)</span>
            {status === "running" && <span className="ml-2 text-blue-500">Running...</span>}
            {status === "completed" && <span className="ml-2 text-emerald-500">Completed!</span>}
            {status === "failed" && <span className="ml-2 text-red-500">Failed</span>}
          </div>
          <div className="flex items-center gap-2">
            {(status === "failed" || status === "completed") && (
              <button
                onClick={onClearTask}
                className="px-3 py-1 text-sm bg-red-100 hover:bg-red-200 text-red-600 rounded transition-colors"
              >
                清除任务
              </button>
            )}
            <button
              onClick={onDismiss}
              className="text-gray-400 hover:text-gray-600 transition-colors p-1"
              aria-label="Dismiss progress"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ease-out ${
              status === "failed" ? "bg-red-500" : "bg-blue-500"
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}
