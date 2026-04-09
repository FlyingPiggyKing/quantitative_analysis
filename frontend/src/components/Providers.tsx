"use client";

import { AnalysisTaskProvider } from "@/contexts/AnalysisTaskContext";
import { AuthProvider } from "@/services/auth";
import { ReactNode } from "react";

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <AnalysisTaskProvider>{children}</AnalysisTaskProvider>
    </AuthProvider>
  );
}
