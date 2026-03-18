"use client";

import type { BrowserAction, SessionMessage } from "@/types/api";
import {
  escalationReasonsForReport,
  featuresForReport,
  formatDateTime,
  formatDuration,
  intentTone,
  parseList,
  questionCount,
  type SessionReport,
  unresolvedForReport,
} from "@/lib/admin-reporting";

type SessionReportDetailProps = {
  report: SessionReport;
  messages: SessionMessage[];
  actions: BrowserAction[];
};

type TimelineItem =
  | { type: "message"; id: string; createdAt: string; payload: SessionMessage }
  | { type: "action"; id: string; createdAt: string; payload: BrowserAction };

function transcriptRoleLabel(role: string) {
  if (role === "user") return "Prospect";
  if (role === "agent") return "Agent";
  return "System";
}

export function SessionReportDetail({ report, messages, actions }: SessionReportDetailProps) {
  const timeline: TimelineItem[] = [
    ...messages.map((message) => ({
      type: "message" as const,
      id: message.id,
      createdAt: message.created_at,
      payload: message,
    })),
    ...actions.map((action) => ({
      type: "action" as const,
      id: action.id,
      createdAt: action.created_at,
      payload: action,
    })),
  ].sort((left, right) => new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime());

  const summary = report.summary;
  const unanswered = unresolvedForReport(report);
  const features = featuresForReport(report);
  const handoff = escalationReasonsForReport(report);
  const objections = parseList(summary?.objections);

  return (
    <div className="space-y-4">
      <section className="admin-panel rounded-[16px] px-5 py-5">
        <p className="admin-eyebrow">Session</p>
        <h2 className="mt-2 text-[1.5rem] tracking-[-0.04em] text-[var(--text-primary)]">
          {formatDateTime(report.session.started_at)}
        </h2>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          Product: {report.workspaceName} · Duration: {formatDuration(summary?.duration_seconds)} · Questions: {questionCount(report)}
        </p>
        <p className="mt-4 admin-note">
          {summary?.summary_text || "No generated summary is available for this session yet."}
        </p>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_320px]">
        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Transcript</p>
          <div className="mt-4 space-y-3">
            {timeline.map((item) =>
              item.type === "message" ? (
                <div key={item.id} className="admin-list-item">
                  <div className="flex items-center justify-between gap-3 text-sm text-[var(--text-secondary)]">
                    <span>{transcriptRoleLabel(item.payload.role)}</span>
                    <span>{formatDateTime(item.payload.created_at)}</span>
                  </div>
                  <p className="mt-2 text-[15px] leading-7 text-[var(--text-primary)]">{item.payload.content}</p>
                  {item.payload.planner_decision ? (
                    <p className="mt-2 text-sm text-[var(--text-tertiary)]">
                      Decision: {item.payload.planner_decision.replaceAll("_", " ")}
                    </p>
                  ) : null}
                </div>
              ) : (
                <div key={item.id} className="rounded-[12px] border border-dashed border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                  → {item.payload.narration || item.payload.action_type}
                </div>
              ),
            )}
          </div>
        </div>

        <div className="space-y-4">
          <section className="admin-panel rounded-[16px] px-5 py-5">
            <p className="admin-eyebrow">Insights</p>
            <div className="mt-4 space-y-4 text-sm text-[var(--text-secondary)]">
              <div>
                <p className="text-[var(--text-primary)]">Intent signal</p>
                <p className="mt-1">{intentTone(summary?.lead_intent_score)}</p>
              </div>
              <div>
                <p className="text-[var(--text-primary)]">Features explored</p>
                {features.length > 0 ? (
                  <ul className="mt-2 space-y-2">
                    {features.slice(0, 4).map((feature) => (
                      <li key={feature}>{feature}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2">No feature themes were captured.</p>
                )}
              </div>
              <div>
                <p className="text-[var(--text-primary)]">Unanswered questions</p>
                {unanswered.length > 0 ? (
                  <ul className="mt-2 space-y-2">
                    {unanswered.map((item) => (
                      <li key={item}>“{item}”</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2">No obvious knowledge gaps were detected.</p>
                )}
              </div>
              <div>
                <p className="text-[var(--text-primary)]">Handoff triggered</p>
                <p className="mt-2">{handoff.length > 0 ? "Yes" : "No"}</p>
              </div>
            </div>
          </section>

          <section className="admin-panel rounded-[16px] px-5 py-5">
            <p className="admin-eyebrow">Attention needed</p>
            {objections.length > 0 ? (
              <ul className="mt-4 space-y-2 text-sm text-[var(--text-secondary)]">
                {objections.slice(0, 4).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-[var(--text-secondary)]">No objections or confusion markers were detected.</p>
            )}
          </section>
        </div>
      </section>
    </div>
  );
}
