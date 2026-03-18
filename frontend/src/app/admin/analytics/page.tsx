"use client";

import {
  AdminShell,
  useAdminWorkspace,
} from "@/components/admin-shell";
import {
  averageDurationSeconds,
  completionRate,
  formatDuration,
  handoffCount,
  highIntentReports,
  topFeatureInterests,
  topObjections,
  topQuestionThemes,
} from "@/lib/admin-reporting";
import { useWorkspaceReportBundle } from "@/lib/use-workspace-report-bundle";

function AnalyticsContent() {
  const { selectedWorkspaceId } = useAdminWorkspace();
  const { bundle, loading, error } = useWorkspaceReportBundle(selectedWorkspaceId);

  if (loading && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">Loading analytics…</div>;
  }

  if (error && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">{error}</div>;
  }

  if (!bundle) return null;

  const metrics = [
    { label: "Sessions", value: String(bundle.analytics.total_sessions) },
    { label: "Avg duration", value: formatDuration(averageDurationSeconds(bundle.reports)) },
    { label: "Completion", value: `${completionRate(bundle.analytics)}%` },
    { label: "Handoffs", value: String(handoffCount(bundle.reports)) },
  ];
  const topQuestions = topQuestionThemes(bundle.reports, 6);
  const interests = topFeatureInterests(bundle.reports, 6);
  const objections = topObjections(bundle.reports, 6);
  const highIntent = highIntentReports(bundle.reports, 5);

  return (
    <div className="space-y-4">
      <section className="grid gap-4 lg:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="admin-metric">
            <p className="admin-eyebrow">{metric.label}</p>
            <p className="mt-4 text-[2rem] tracking-[-0.05em] text-[var(--text-primary)]">{metric.value}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <div className="space-y-4">
          <div className="admin-panel rounded-[16px] px-5 py-5">
            <p className="admin-eyebrow">Detailed reports</p>
            <h2 className="mt-2 text-[1.4rem] tracking-[-0.04em] text-[var(--text-primary)]">Question themes</h2>
            <div className="mt-4 space-y-3">
              {topQuestions.length > 0 ? topQuestions.map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-[var(--text-primary)]">{item.label}</span>
                    <span className="text-[var(--text-secondary)]">{item.count}</span>
                  </div>
                  <div className="admin-stat-bar mt-2">
                    <div className="admin-stat-fill" style={{ width: `${Math.min(100, item.count * 20)}%` }} />
                  </div>
                </div>
              )) : <p className="text-sm text-[var(--text-secondary)]">No recurring question themes yet.</p>}
            </div>
          </div>

          <div className="admin-panel rounded-[16px] px-5 py-5">
            <p className="admin-eyebrow">Detailed reports</p>
            <h2 className="mt-2 text-[1.4rem] tracking-[-0.04em] text-[var(--text-primary)]">Feature interest and objections</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-sm text-[var(--text-primary)]">Features explored</p>
                <ul className="mt-3 space-y-2 text-sm text-[var(--text-secondary)]">
                  {interests.length > 0 ? interests.map((item) => <li key={item.label}>{item.label}</li>) : <li>No feature interest captured yet.</li>}
                </ul>
              </div>
              <div>
                <p className="text-sm text-[var(--text-primary)]">Objections</p>
                <ul className="mt-3 space-y-2 text-sm text-[var(--text-secondary)]">
                  {objections.length > 0 ? objections.map((item) => <li key={item.label}>{item.label}</li>) : <li>No objections captured yet.</li>}
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Top sessions</p>
          <h2 className="mt-2 text-[1.4rem] tracking-[-0.04em] text-[var(--text-primary)]">Highest intent sessions</h2>
          <div className="mt-4 space-y-3">
            {highIntent.map((report) => (
              <div key={report.session.id} className="admin-list-item">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm text-[var(--text-primary)]">{report.session.buyer_name || "Anonymous prospect"}</p>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">{report.summary?.summary_text || "No summary."}</p>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">{report.summary?.lead_intent_score ?? 0}/100</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

export default function AdminAnalyticsPage() {
  return (
    <AdminShell
      title="Analytics"
      description="Detailed metrics and theme breakdowns for the currently selected product."
    >
      <AnalyticsContent />
    </AdminShell>
  );
}
