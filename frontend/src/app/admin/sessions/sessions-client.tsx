"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { AdminShell, useAdminWorkspace } from "@/components/admin-shell";
import { SessionReportDetail } from "@/components/session-report-detail";
import { api } from "@/lib/api";
import {
  escalationReasonsForReport,
  formatDateTime,
  formatDuration,
  questionCount,
  type SessionReport,
} from "@/lib/admin-reporting";
import { useWorkspaceReportBundle } from "@/lib/use-workspace-report-bundle";
import type { BrowserAction, SessionMessage } from "@/types/api";

export function AdminSessionsClient() {
  return (
    <AdminShell
      title="Sessions"
      description="Review demo sessions in a report-first format: what happened, what the prospect asked, and what needs attention next."
    >
      <AdminSessionsContent />
    </AdminShell>
  );
}

function AdminSessionsContent() {
  const searchParams = useSearchParams();
  const { selectedWorkspaceId } = useAdminWorkspace();
  const selectedFromQuery = searchParams?.get("session") ?? null;
  const { bundle, loading, error } = useWorkspaceReportBundle(selectedWorkspaceId);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(selectedFromQuery);
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [actions, setActions] = useState<BrowserAction[]>([]);

  useEffect(() => {
    if (!bundle?.reports.length) return;
    setSelectedSessionId((current) => current ?? bundle.reports[0]?.session.id ?? null);
  }, [bundle]);

  useEffect(() => {
    if (!selectedSessionId) return;
    const sessionId = selectedSessionId;
    let cancelled = false;

    async function loadSessionDetail() {
      const [sessionMessages, sessionActions] = await Promise.all([
        api.getMessages(sessionId),
        api.getSessionActions(sessionId),
      ]);
      if (!cancelled) {
        setMessages(sessionMessages);
        setActions(sessionActions);
      }
    }

    void loadSessionDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedSessionId]);

  const selectedReport = useMemo<SessionReport | null>(
    () => bundle?.reports.find((report) => report.session.id === selectedSessionId) ?? null,
    [bundle, selectedSessionId],
  );
  return loading && !bundle ? (
    <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">Loading sessions…</div>
  ) : error && !bundle ? (
    <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">{error}</div>
  ) : !bundle ? null : (
    <div className="space-y-4">
      <section className="admin-panel rounded-[16px] px-5 py-5">
        <div className="flex flex-wrap gap-3">
          <div className="admin-filter">Product: {bundle.workspace.name}</div>
          <div className="admin-filter">Sessions: {bundle.reports.length}</div>
          <div className="admin-filter">View: detailed reports</div>
        </div>

        <div className="mt-5 overflow-hidden rounded-[12px] border border-[var(--border-subtle)]">
          <div className="hidden grid-cols-[180px_minmax(0,1fr)_110px_110px_90px] gap-4 bg-[var(--surface-muted)] px-4 py-3 text-xs uppercase tracking-[0.08em] text-[var(--text-tertiary)] md:grid">
            <span>Date</span>
            <span>Prospect</span>
            <span>Duration</span>
            <span>Questions</span>
            <span>Handoff</span>
          </div>
          {bundle.reports.map((report) => (
            <button
              key={report.session.id}
              type="button"
              onClick={() => setSelectedSessionId(report.session.id)}
              className="admin-table-row w-full px-4 py-4 text-left"
            >
              <div className="grid gap-3 md:grid-cols-[180px_minmax(0,1fr)_110px_110px_90px] md:items-center md:gap-4">
                <p className="text-sm text-[var(--text-secondary)]">{formatDateTime(report.session.started_at)}</p>
                <div>
                  <p className="text-sm text-[var(--text-primary)]">{report.session.buyer_name || "Anonymous prospect"}</p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">{report.summary?.summary_text || "No summary available."}</p>
                </div>
                <p className="text-sm text-[var(--text-secondary)]">{formatDuration(report.summary?.duration_seconds)}</p>
                <p className="text-sm text-[var(--text-secondary)]">{questionCount(report)}</p>
                <p className="text-sm text-[var(--text-secondary)]">{escalationReasonsForReport(report).length > 0 ? "Yes" : "No"}</p>
              </div>
            </button>
          ))}
        </div>
      </section>

      {selectedReport ? (
        <SessionReportDetail report={selectedReport} messages={messages} actions={actions} />
      ) : (
        <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">Select a session to inspect the full report.</div>
      )}
    </div>
  );
}
