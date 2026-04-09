"use client";

import { AnalysisTaskProvider } from "@/contexts/AnalysisTaskContext";
import { ReactNode } from "react";

export default function Providers({ children }: { children: ReactNode }) {
  return <AnalysisTaskProvider>{children}</AnalysisTaskProvider>;
}
