import { api } from "@/lib/api";
import type { DemoSession, SessionSummary, Workspace, WorkspaceAnalytics } from "@/types/api";

export type SessionReport = {
  session: DemoSession;
  summary: SessionSummary | null;
  workspaceId: string;
  workspaceName: string;
};

export type WorkspaceReportBundle = {
  workspace: Workspace;
  analytics: WorkspaceAnalytics;
  reports: SessionReport[];
};

type RankedValue = {
  label: string;
  count: number;
};

const STOP_WORDS = new Set([
  "about",
  "after",
  "agent",
  "also",
  "been",
  "being",
  "between",
  "could",
  "demo",
  "does",
  "from",
  "have",
  "into",
  "just",
  "more",
  "need",
  "prospect",
  "product",
  "session",
  "that",
  "their",
  "them",
  "they",
  "this",
  "through",
  "what",
  "when",
  "where",
  "which",
  "with",
  "would",
  "your",
]);

export function parseList(source?: string | null): string[] {
  if (!source) return [];
  try {
    const parsed = JSON.parse(source);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((value): value is string => typeof value === "string" && value.trim().length > 0);
  } catch {
    return [];
  }
}

export function formatDateTime(source?: string | null): string {
  if (!source) return "Recently";
  const date = new Date(source);
  if (Number.isNaN(date.getTime())) return "Recently";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatShortDate(source?: string | null): string {
  if (!source) return "Recently";
  const date = new Date(source);
  if (Number.isNaN(date.getTime())) return "Recently";
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function formatRelativeTime(source?: string | null): string {
  if (!source) return "Recently";
  const date = new Date(source);
  if (Number.isNaN(date.getTime())) return "Recently";
  const minutes = Math.max(1, Math.round((Date.now() - date.getTime()) / 60000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export function formatDuration(seconds?: number | null): string {
  if (!seconds || seconds <= 0) return "0:00";
  const safe = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(safe / 60);
  const remaining = safe % 60;
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

export function averageDurationSeconds(reports: SessionReport[]): number {
  const durations = reports
    .map((report) => report.summary?.duration_seconds ?? 0)
    .filter((value) => value > 0);
  if (durations.length === 0) return 0;
  return Math.round(durations.reduce((total, value) => total + value, 0) / durations.length);
}

export function completionRate(analytics: WorkspaceAnalytics): number {
  if (!analytics.total_sessions) return 0;
  return Math.round((analytics.completed_sessions / analytics.total_sessions) * 100);
}

export function handoffCount(reports: SessionReport[]): number {
  return reports.filter((report) => parseList(report.summary?.escalation_reasons).length > 0).length;
}

export function handoffRate(reports: SessionReport[]): number {
  if (reports.length === 0) return 0;
  return Math.round((handoffCount(reports) / reports.length) * 100);
}

export function questionCount(report: SessionReport): number {
  return parseList(report.summary?.top_questions).length;
}

export function featuresForReport(report: SessionReport): string[] {
  return parseList(report.summary?.features_interest);
}

export function objectionsForReport(report: SessionReport): string[] {
  return parseList(report.summary?.objections);
}

export function unresolvedForReport(report: SessionReport): string[] {
  return parseList(report.summary?.unresolved_items);
}

export function escalationReasonsForReport(report: SessionReport): string[] {
  return parseList(report.summary?.escalation_reasons);
}

export function intentLabel(score?: number | null): "Positive" | "Neutral" | "Negative" {
  const value = score ?? 0;
  if (value >= 70) return "Positive";
  if (value >= 40) return "Neutral";
  return "Negative";
}

export function intentTone(score?: number | null): string {
  const label = intentLabel(score);
  if (label === "Positive") return "High intent";
  if (label === "Neutral") return "Mixed interest";
  return "Low confidence";
}

export function productState(workspace: Workspace, reportCount = 0, knowledgeCount = 0): "Draft" | "Configuring" | "Ready" | "Live" {
  if (workspace.is_active) return "Live";
  if (workspace.product_url && knowledgeCount > 0 && reportCount > 0) return "Ready";
  if (workspace.product_url || knowledgeCount > 0) return "Configuring";
  return "Draft";
}

function normalizePhrase(value: string): string {
  return value.trim().replace(/\s+/g, " ").replace(/[?!.]+$/g, "");
}

function rankExact(values: string[], limit: number): RankedValue[] {
  const counts = new Map<string, number>();
  for (const value of values) {
    const normalized = normalizePhrase(value);
    if (!normalized) continue;
    counts.set(normalized, (counts.get(normalized) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
    .slice(0, limit);
}

function tokenizeWords(values: string[]): string[] {
  const tokens: string[] = [];
  for (const value of values) {
    const words = normalizePhrase(value)
      .toLowerCase()
      .replace(/[^a-z0-9\s/-]/g, " ")
      .split(/\s+/)
      .filter((word) => word.length > 2 && !STOP_WORDS.has(word));
    tokens.push(...words);
    for (let index = 0; index < words.length - 1; index += 1) {
      tokens.push(`${words[index]} ${words[index + 1]}`);
    }
  }
  return tokens;
}

export function topKeywordTerms(reports: SessionReport[], limit = 12): RankedValue[] {
  const phrases = reports.flatMap((report) => [
    ...parseList(report.summary?.top_questions),
    ...parseList(report.summary?.features_interest),
    ...parseList(report.summary?.objections),
  ]);
  const tokenCounts = new Map<string, number>();
  for (const token of tokenizeWords(phrases)) {
    tokenCounts.set(token, (tokenCounts.get(token) ?? 0) + 1);
  }
  return [...tokenCounts.entries()]
    .map(([label, count]) => ({ label, count }))
    .filter((item) => item.count > 1)
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
    .slice(0, limit);
}

export function topQuestionThemes(reports: SessionReport[], limit = 8): RankedValue[] {
  return rankExact(reports.flatMap((report) => parseList(report.summary?.top_questions)), limit);
}

export function topFeatureInterests(reports: SessionReport[], limit = 8): RankedValue[] {
  return rankExact(reports.flatMap((report) => parseList(report.summary?.features_interest)), limit);
}

export function topObjections(reports: SessionReport[], limit = 8): RankedValue[] {
  return rankExact(reports.flatMap((report) => parseList(report.summary?.objections)), limit);
}

export function competitorMentions(reports: SessionReport[], limit = 10): RankedValue[] {
  const phrases = reports.flatMap((report) => [
    ...parseList(report.summary?.top_questions),
    ...parseList(report.summary?.objections),
  ]);
  const candidates = phrases.filter((value) => /competitor|alternative|currently use|switch|against/i.test(value));
  return rankExact(candidates, limit);
}

export function recentReports(reports: SessionReport[], count = 5): SessionReport[] {
  return [...reports]
    .sort(
      (left, right) =>
        new Date(right.session.started_at || 0).getTime() -
        new Date(left.session.started_at || 0).getTime(),
    )
    .slice(0, count);
}

export function highIntentReports(reports: SessionReport[], count = 5): SessionReport[] {
  return [...reports]
    .sort(
      (left, right) =>
        (right.summary?.lead_intent_score ?? 0) - (left.summary?.lead_intent_score ?? 0),
    )
    .slice(0, count);
}

export function unresolvedHighlights(reports: SessionReport[]): string[] {
  return rankExact(reports.flatMap((report) => unresolvedForReport(report)), 6).map((item) => item.label);
}

export function intentIndicators(reports: SessionReport[]) {
  const definitions = [
    {
      label: "Asked about pricing or plans",
      match: (report: SessionReport) =>
        /pricing|price|plan|cost|quote/i.test(parseList(report.summary?.top_questions).join(" ")),
    },
    {
      label: "Asked about trial or signup",
      match: (report: SessionReport) =>
        /trial|sign up|signup|start|book/i.test(parseList(report.summary?.top_questions).join(" ")),
    },
    {
      label: "Compared with a current tool",
      match: (report: SessionReport) =>
        /competitor|alternative|currently use|switch/i.test(
          [...parseList(report.summary?.top_questions), ...parseList(report.summary?.objections)].join(" "),
        ),
    },
    {
      label: "Asked about onboarding",
      match: (report: SessionReport) =>
        /onboarding|setup|migration|import/i.test(
          [...parseList(report.summary?.top_questions), ...parseList(report.summary?.features_interest)].join(" "),
        ),
    },
    {
      label: "Asked about team or seats",
      match: (report: SessionReport) =>
        /team|seat|user/i.test(parseList(report.summary?.top_questions).join(" ")),
    },
    {
      label: "Requested human follow-up",
      match: (report: SessionReport) => escalationReasonsForReport(report).length > 0,
    },
    {
      label: "Explored multiple feature areas",
      match: (report: SessionReport) => featuresForReport(report).length >= 3,
    },
    {
      label: "Stayed for 15+ minutes",
      match: (report: SessionReport) => (report.summary?.duration_seconds ?? 0) >= 900,
    },
  ];

  return definitions.map((definition) => {
    const occurrences = reports.filter(definition.match).length;
    return {
      label: definition.label,
      occurrences,
      percentage: reports.length === 0 ? 0 : Math.round((occurrences / reports.length) * 100),
    };
  });
}

export function negativeExperiencePatterns(reports: SessionReport[]) {
  const patterns = [
    {
      label: "Agent could not answer clearly",
      count: reports.filter((report) => unresolvedForReport(report).length > 0).length,
      action: "Review gaps",
    },
    {
      label: "Prospect seemed confused",
      count: reports.filter((report) =>
        objectionsForReport(report).some((item) => /confused|not sure|don't understand|complex|difficult/i.test(item)),
      ).length,
      action: "Review sessions",
    },
    {
      label: "Early abandonment",
      count: reports.filter((report) => {
        const duration = report.summary?.duration_seconds ?? 0;
        return duration > 0 && duration < 120;
      }).length,
      action: "Check loading",
    },
    {
      label: "Repeated questions",
      count: reports.filter((report) => {
        const questions = parseList(report.summary?.top_questions).map((value) => normalizePhrase(value).toLowerCase());
        return new Set(questions).size !== questions.length && questions.length > 1;
      }).length,
      action: "Improve clarity",
    },
  ];

  return patterns.filter((pattern) => pattern.count > 0);
}

export function deriveContacts(reports: SessionReport[]) {
  const grouped = new Map<string, SessionReport[]>();
  for (const report of reports) {
    const key =
      report.session.buyer_email ||
      report.session.buyer_name ||
      `Anonymous ${report.session.id.slice(0, 6)}`;
    const current = grouped.get(key) ?? [];
    current.push(report);
    grouped.set(key, current);
  }

  return [...grouped.entries()]
    .map(([label, items]) => {
      const sorted = [...items].sort(
        (left, right) =>
          new Date(right.session.started_at || 0).getTime() -
          new Date(left.session.started_at || 0).getTime(),
      );
      const avgScore = Math.round(
        sorted.reduce((total, report) => total + (report.summary?.lead_intent_score ?? 0), 0) /
          Math.max(sorted.length, 1),
      );
      const interests = topFeatureInterests(sorted, 2).map((item) => item.label);
      return {
        label,
        sessions: sorted.length,
        averageIntent: avgScore,
        lastSeen: sorted[0]?.session.started_at ?? null,
        interests,
      };
    })
    .sort((left, right) => right.averageIntent - left.averageIntent || right.sessions - left.sessions);
}

export async function loadWorkspaceReportBundle(workspaceId: string): Promise<WorkspaceReportBundle> {
  const [workspace, analytics, sessions] = await Promise.all([
    api.getWorkspace(workspaceId),
    api.getWorkspaceAnalytics(workspaceId),
    api.getWorkspaceSessions(workspaceId),
  ]);

  const summaries = await Promise.all(
    sessions.map(async (session: DemoSession) => {
      try {
        return await api.getSessionSummary(session.id);
      } catch {
        return null;
      }
    }),
  );

  return {
    workspace,
    analytics,
    reports: sessions.map((session: DemoSession, index: number) => ({
      session,
      summary: summaries[index],
      workspaceId: workspace.id,
      workspaceName: workspace.name,
    })),
  };
}
