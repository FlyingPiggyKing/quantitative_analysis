"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface AnalysisTaskContextType {
  activeTaskId: string | null;
  setActiveTaskId: (taskId: string | null) => void;
}

const AnalysisTaskContext = createContext<AnalysisTaskContextType | undefined>(undefined);

export function AnalysisTaskProvider({ children }: { children: ReactNode }) {
  const [activeTaskId, setActiveTaskIdState] = useState<string | null>(null);

  const setActiveTaskId = useCallback((taskId: string | null) => {
    setActiveTaskIdState(taskId);
    if (taskId) {
      localStorage.setItem("active_analysis_task_id", taskId);
    } else {
      localStorage.removeItem("active_analysis_task_id");
    }
  }, []);

  return (
    <AnalysisTaskContext.Provider value={{ activeTaskId, setActiveTaskId }}>
      {children}
    </AnalysisTaskContext.Provider>
  );
}

export function useAnalysisTask() {
  const context = useContext(AnalysisTaskContext);
  if (context === undefined) {
    throw new Error("useAnalysisTask must be used within an AnalysisTaskProvider");
  }
  return context;
}
