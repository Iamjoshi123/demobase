"use client";

import { AdminShell, useAdminWorkspace } from "@/components/admin-shell";
import {
  competitorMentions,
  topKeywordTerms,
  topQuestionThemes,
} from "@/lib/admin-reporting";
import { useWorkspaceReportBundle } from "@/lib/use-workspace-report-bundle";

function KeywordsContent() {
  const { selectedWorkspaceId } = useAdminWorkspace();
  const { bundle, loading, error } = useWorkspaceReportBundle(selectedWorkspaceId);

  if (loading && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">Loading keyword trends…</div>;
  }

  if (error && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">{error}</div>;
  }

  if (!bundle) return null;

  const keywords = topKeywordTerms(bundle.reports, 12);
  const themes = topQuestionThemes(bundle.reports, 8);
  const competitors = competitorMentions(bundle.reports, 6);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_360px]">
      <div className="space-y-4">
        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Keywords</p>
          <h2 className="mt-2 text-[1.4rem] tracking-[-0.04em] text-[var(--text-primary)]">Top keywords and topics</h2>
          <div className="mt-4 space-y-3">
            {keywords.length > 0 ? keywords.map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-[var(--text-primary)]">{item.label}</span>
                  <span className="text-[var(--text-secondary)]">{item.count}</span>
                </div>
                <div className="admin-stat-bar mt-2">
                  <div className="admin-stat-fill" style={{ width: `${Math.min(100, item.count * 16)}%` }} />
                </div>
              </div>
            )) : <p className="text-sm text-[var(--text-secondary)]">Not enough session data yet.</p>}
          </div>
        </div>

        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Question themes</p>
          <div className="mt-4 space-y-3 text-sm text-[var(--text-secondary)]">
            {themes.length > 0 ? themes.map((item) => (
              <div key={item.label} className="admin-list-item">
                <p className="text-[var(--text-primary)]">{item.label}</p>
                <p className="mt-1">{item.count} recurring mentions</p>
              </div>
            )) : <p>No clustered questions yet.</p>}
          </div>
        </div>
      </div>

      <div className="admin-panel rounded-[16px] px-5 py-5">
        <p className="admin-eyebrow">Competitor mentions</p>
        <h2 className="mt-2 text-[1.4rem] tracking-[-0.04em] text-[var(--text-primary)]">Comparison signals</h2>
        <div className="mt-4 space-y-3 text-sm text-[var(--text-secondary)]">
          {competitors.length > 0 ? competitors.map((item) => (
            <div key={item.label} className="admin-list-item">
              <p className="text-[var(--text-primary)]">{item.label}</p>
              <p className="mt-1">{item.count} sessions mentioned this theme.</p>
            </div>
          )) : <p>No competitor comparisons have been detected yet.</p>}
        </div>
      </div>
    </div>
  );
}

export default function AdminKeywordsPage() {
  return (
    <AdminShell
      title="Keywords & Topics"
      description="See what prospects talk about most, which questions recur, and where competitor comparisons appear."
    >
      <KeywordsContent />
    </AdminShell>
  );
}
