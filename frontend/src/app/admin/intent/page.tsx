"use client";

import { AdminShell, useAdminWorkspace } from "@/components/admin-shell";
import {
  highIntentReports,
  intentIndicators,
  intentLabel,
  negativeExperiencePatterns,
} from "@/lib/admin-reporting";
import { useWorkspaceReportBundle } from "@/lib/use-workspace-report-bundle";

function IntentContent() {
  const { selectedWorkspaceId } = useAdminWorkspace();
  const { bundle, loading, error } = useWorkspaceReportBundle(selectedWorkspaceId);

  if (loading && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">Loading intent signals…</div>;
  }

  if (error && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">{error}</div>;
  }

  if (!bundle) return null;

  const sentiments = {
    Positive: bundle.reports.filter((report) => intentLabel(report.summary?.lead_intent_score) === "Positive").length,
    Neutral: bundle.reports.filter((report) => intentLabel(report.summary?.lead_intent_score) === "Neutral").length,
    Negative: bundle.reports.filter((report) => intentLabel(report.summary?.lead_intent_score) === "Negative").length,
  };
  const total = Math.max(bundle.reports.length, 1);
  const indicators = intentIndicators(bundle.reports);
  const patterns = negativeExperiencePatterns(bundle.reports);
  const highIntent = highIntentReports(bundle.reports, 6);

  return (
    <div className="space-y-4">
      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Sentiment overview</p>
          <div className="mt-4 space-y-4">
            {Object.entries(sentiments).map(([label, count]) => (
              <div key={label}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-[var(--text-primary)]">{label}</span>
                  <span className="text-[var(--text-secondary)]">{Math.round((count / total) * 100)}%</span>
                </div>
                <div className="admin-stat-bar mt-2">
                  <div className="admin-stat-fill" style={{ width: `${Math.round((count / total) * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Intent indicators</p>
          <div className="mt-4 space-y-3 text-sm text-[var(--text-secondary)]">
            {indicators.map((item) => (
              <div key={item.label} className="admin-list-item">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[var(--text-primary)]">{item.label}</span>
                  <span>{item.percentage}%</span>
                </div>
                <p className="mt-1">{item.occurrences} sessions</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_360px]">
        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Session intent breakdown</p>
          <div className="mt-4 space-y-3">
            {highIntent.map((report) => (
              <div key={report.session.id} className="admin-list-item">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm text-[var(--text-primary)]">{report.session.buyer_name || "Anonymous prospect"}</p>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">{report.summary?.summary_text || "No summary available."}</p>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">{report.summary?.lead_intent_score ?? 0}/100</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Negative patterns</p>
          <div className="mt-4 space-y-3 text-sm text-[var(--text-secondary)]">
            {patterns.length > 0 ? patterns.map((pattern) => (
              <div key={pattern.label} className="admin-list-item">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[var(--text-primary)]">{pattern.label}</span>
                  <span>{pattern.count}</span>
                </div>
                <p className="mt-1">{pattern.action}</p>
              </div>
            )) : <p>No negative clusters detected yet.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

export default function AdminIntentPage() {
  return (
    <AdminShell
      title="Intent Signals"
      description="Track buying signals, session sentiment, and the patterns that correlate with strong or weak demo outcomes."
    >
      <IntentContent />
    </AdminShell>
  );
}
