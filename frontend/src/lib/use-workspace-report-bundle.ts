"use client";

import { useEffect, useState } from "react";

import {
  loadWorkspaceReportBundle,
  type WorkspaceReportBundle,
} from "@/lib/admin-reporting";

export function useWorkspaceReportBundle(workspaceId: string | null) {
  const [bundle, setBundle] = useState<WorkspaceReportBundle | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    const activeWorkspaceId = workspaceId;
    let cancelled = false;

    async function loadBundle() {
      setLoading(true);
      setError(null);
      try {
        const nextBundle = await loadWorkspaceReportBundle(activeWorkspaceId);
        if (!cancelled) {
          setBundle(nextBundle);
        }
      } catch (cause: any) {
        if (!cancelled) {
          setError(cause.message || "Could not load report data.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadBundle();
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  return { bundle, loading, error };
}
