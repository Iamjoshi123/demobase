"use client";

import Link from "next/link";

import { AdminShell, useAdminWorkspace } from "@/components/admin-shell";
import {
  averageDurationSeconds,
  completionRate,
  formatDateTime,
  formatDuration,
  handoffRate,
  recentReports,
  topFeatureInterests,
  topObjections,
  topQuestionThemes,
  unresolvedHighlights,
} from "@/lib/admin-reporting";
import { useWorkspaceReportBundle } from "@/lib/use-workspace-report-bundle";

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="admin-metric">
            <div className="h-4 w-20 rounded animate-shimmer" />
            <div className="mt-4 h-8 w-24 rounded animate-shimmer" />
            <div className="mt-2 h-4 w-28 rounded animate-shimmer" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_360px]">
        <div className="admin-panel rounded-[16px] px-5 py-5">
          <div className="h-5 w-40 rounded animate-shimmer" />
          <div className="mt-4 space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-16 rounded animate-shimmer" />
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <div className="admin-panel rounded-[16px] px-5 py-5">
            <div className="h-5 w-28 rounded animate-shimmer" />
            <div className="mt-4 h-24 rounded animate-shimmer" />
          </div>
          <div className="admin-panel rounded-[16px] px-5 py-5">
            <div className="h-5 w-28 rounded animate-shimmer" />
            <div className="mt-4 h-24 rounded animate-shimmer" />
          </div>
        </div>
      </div>
    </div>
  );
}

function DashboardContent() {
  const { selectedWorkspaceId, selectedWorkspace } = useAdminWorkspace();
  const { bundle, loading, error } = useWorkspaceReportBundle(selectedWorkspaceId);

  if (!selectedWorkspaceId && !selectedWorkspace) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">Create a product first to see dashboard insights.</div>;
  }

  if (loading && !bundle) {
    return <DashboardSkeleton />;
  }

  if (error && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">{error}</div>;
  }

  if (!bundle) {
    return null;
  }

  const metrics = [
    {
      label: "Total sessions",
      value: String(bundle.analytics.total_sessions),
      note: `${bundle.analytics.completed_sessions} completed demos`,
    },
    {
      label: "Avg duration",
      value: formatDuration(averageDurationSeconds(bundle.reports)),
      note: "Across completed sessions",
    },
    {
      label: "Completion",
      value: `${completionRate(bundle.analytics)}%`,
      note: "Sessions reaching an end state",
    },
    {
      label: "Handoff",
      value: `${handoffRate(bundle.reports)}%`,
      note: "Sessions that requested follow-up",
    },
  ];

  const recent = recentReports(bundle.reports, 5);
  const topQuestions = topQuestionThemes(bundle.reports, 4);
  const interests = topFeatureInterests(bundle.reports, 4);
  const objections = topObjections(bundle.reports, 4);
  const gaps = unresolvedHighlights(bundle.reports);

  return (
    <div className="space-y-4">
      <section className="grid gap-4 lg:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="admin-metric">
            <p className="admin-eyebrow">{metric.label}</p>
            <p className="mt-4 text-[2rem] tracking-[-0.05em] text-[var(--text-primary)]">{metric.value}</p>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">{metric.note}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_360px]">
        <div className="admin-panel rounded-[16px] px-5 py-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="admin-eyebrow">What happened</p>
              <h2 className="mt-2 text-[1.5rem] tracking-[-0.04em] text-[var(--text-primary)]">Recent sessions</h2>
            </div>
            <Link href={`/admin/sessions?workspaceId=${bundle.workspace.id}`} className="btn-secondary">
              View all
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {recent.map((report) => (
              <Link
                key={report.session.id}
                href={`/admin/sessions?workspaceId=${bundle.workspace.id}&session=${report.session.id}`}
                className="admin-list-item block"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm text-[var(--text-primary)]">{report.session.buyer_name || "Anonymous prospect"}</p>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">
                      {formatDateTime(report.session.started_at)} · {formatDuration(report.summary?.duration_seconds)}
                    </p>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">{report.summary?.lead_intent_score ?? 0}/100</p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="admin-panel rounded-[16px] px-5 py-5">
            <p className="admin-eyebrow">What is working</p>
            <div className="mt-4 space-y-4">
              <div>
                <p className="text-sm text-[var(--text-primary)]">Top questions</p>
                <ul className="mt-2 space-y-2 text-sm text-[var(--text-secondary)]">
                  {topQuestions.length > 0 ? topQuestions.map((item) => <li key={item.label}>{item.label}</li>) : <li>No repeated themes yet.</li>}
                </ul>
              </div>
              <div>
                <p className="text-sm text-[var(--text-primary)]">Features explored</p>
                <ul className="mt-2 space-y-2 text-sm text-[var(--text-secondary)]">
                  {interests.length > 0 ? interests.map((item) => <li key={item.label}>{item.label}</li>) : <li>No feature patterns yet.</li>}
                </ul>
              </div>
            </div>
          </div>

          <div className="admin-panel rounded-[16px] px-5 py-5">
            <p className="admin-eyebrow">What needs attention</p>
            <div className="mt-4 space-y-4">
              <div>
                <p className="text-sm text-[var(--text-primary)]">Knowledge gaps</p>
                <ul className="mt-2 space-y-2 text-sm text-[var(--text-secondary)]">
                  {gaps.length > 0 ? gaps.map((item) => <li key={item}>“{item}”</li>) : <li>No unresolved questions detected.</li>}
                </ul>
              </div>
              <div>
                <p className="text-sm text-[var(--text-primary)]">Objections</p>
                <ul className="mt-2 space-y-2 text-sm text-[var(--text-secondary)]">
                  {objections.length > 0 ? objections.map((item) => <li key={item.label}>{item.label}</li>) : <li>No objections captured yet.</li>}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function AdminDashboardPage() {
  return (
    <AdminShell
      title="Dashboard"
      description="Your morning briefing for demo activity, engagement, and the gaps worth fixing next."
      actions={<Link href="/admin/products" className="btn-secondary">Manage products</Link>}
    >
      <DashboardContent />
    </AdminShell>
  );
}
