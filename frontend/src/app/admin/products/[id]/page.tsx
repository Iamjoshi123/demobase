"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { SessionReportDetail } from "@/components/session-report-detail";
import { api } from "@/lib/api";
import {
  escalationReasonsForReport,
  formatDuration,
  questionCount,
  type SessionReport,
} from "@/lib/admin-reporting";
import type { BrowserAction, SessionMessage, SessionSummary } from "@/types/api";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "knowledge", label: "Knowledge" },
  { key: "agent", label: "Agent" },
  { key: "sessions", label: "Sessions" },
  { key: "share", label: "Share" },
] as const;

function formatDate(source?: string | null) {
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

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const workspaceId = params?.id ?? "";
  const [workspace, setWorkspace] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [credentials, setCredentials] = useState<any[]>([]);
  const [recipes, setRecipes] = useState<any[]>([]);
  const [policies, setPolicies] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [sessionSummaries, setSessionSummaries] = useState<Record<string, SessionSummary | null>>({});
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["key"]>("overview");
  const [docForm, setDocForm] = useState({ filename: "", content_text: "", file_type: "md" });
  const [credForm, setCredForm] = useState({ label: "", login_url: "", username: "", password: "" });
  const [policyForm, setPolicyForm] = useState({ rule_type: "blocked_topic", pattern: "", description: "", action: "refuse", severity: "high" });
  const [recipeForm, setRecipeForm] = useState({ name: "", description: "", trigger_phrases: "", steps_json: "[]", priority: 0 });
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(searchParams?.get("session") ?? null);
  const [sessionMessages, setSessionMessages] = useState<SessionMessage[]>([]);
  const [sessionActions, setSessionActions] = useState<BrowserAction[]>([]);

  useEffect(() => {
    const requestedTab = searchParams?.get("tab");
    if (requestedTab && TABS.some((tab) => tab.key === requestedTab)) {
      setActiveTab(requestedTab as (typeof TABS)[number]["key"]);
    }
  }, [searchParams]);

  const loadAll = useCallback(async () => {
    const [ws, docs, creds, recs, pols, sess] = await Promise.all([
      api.getWorkspace(workspaceId),
      api.listDocuments(workspaceId),
      api.listCredentials(workspaceId),
      api.listRecipes(workspaceId),
      api.listPolicies(workspaceId),
      api.getWorkspaceSessions(workspaceId),
    ]);
    setWorkspace(ws);
    setDocuments(docs);
    setCredentials(creds);
    setRecipes(recs);
    setPolicies(pols);
    setSessions(sess);
    setSelectedSessionId((current) => current ?? sess[0]?.id ?? null);
    const summaries = await Promise.all(
      sess.map(async (session: any) => {
        try {
          return [session.id, await api.getSessionSummary(session.id)] as const;
        } catch {
          return [session.id, null] as const;
        }
      }),
    );
    setSessionSummaries(Object.fromEntries(summaries));
  }, [workspaceId]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    async function loadSession() {
      if (!selectedSessionId) return;
      const [messages, actions] = await Promise.all([
        api.getMessages(selectedSessionId),
        api.getSessionActions(selectedSessionId),
      ]);
      setSessionMessages(messages);
      setSessionActions(actions);
    }
    void loadSession();
  }, [selectedSessionId]);

  async function saveOverview(event: React.FormEvent) {
    event.preventDefault();
    await api.updateWorkspace(workspaceId, {
      name: workspace.name,
      description: workspace.description,
      product_url: workspace.product_url,
      allowed_domains: workspace.allowed_domains,
      browser_auth_mode: workspace.browser_auth_mode,
    });
    await loadAll();
  }

  async function uploadDocument(event: React.FormEvent) {
    event.preventDefault();
    const formData = new FormData();
    formData.append("filename", docForm.filename);
    formData.append("file_type", docForm.file_type);
    formData.append("content_text", docForm.content_text);
    await api.uploadDocument(workspaceId, formData);
    setDocForm({ filename: "", content_text: "", file_type: "md" });
    await loadAll();
  }

  async function addCredential(event: React.FormEvent) {
    event.preventDefault();
    await api.addCredential(workspaceId, credForm);
    setCredForm({ label: "", login_url: "", username: "", password: "" });
    await loadAll();
  }

  async function addPolicy(event: React.FormEvent) {
    event.preventDefault();
    await api.createPolicy(workspaceId, policyForm);
    setPolicyForm({ rule_type: "blocked_topic", pattern: "", description: "", action: "refuse", severity: "high" });
    await loadAll();
  }

  async function addRecipe(event: React.FormEvent) {
    event.preventDefault();
    await api.createRecipe(workspaceId, recipeForm);
    setRecipeForm({ name: "", description: "", trigger_phrases: "", steps_json: "[]", priority: 0 });
    await loadAll();
  }

  const demoLink = typeof window !== "undefined" ? `${window.location.origin}/demo/${workspace?.public_token || ""}` : `/demo/${workspace?.public_token || ""}`;
  const liveLink = typeof window !== "undefined" ? `${window.location.origin}/meet/${workspace?.public_token || ""}` : `/meet/${workspace?.public_token || ""}`;
  const embedCode = `<iframe src="${demoLink}" title="Interactive product demo" style="width:100%;min-height:720px;border:0;border-radius:24px;" allow="microphone; autoplay"></iframe>`;

  const checklist = useMemo(() => {
    if (!workspace) return [];
    return [
      { label: "Product details added", done: Boolean(workspace.name && workspace.product_url), tab: "overview" },
      { label: "Demo connection configured", done: credentials.length > 0 || workspace.browser_auth_mode === "none", tab: "agent" },
      { label: `Knowledge base has ${documents.length} entries`, done: documents.length > 0, tab: "knowledge" },
      { label: "Session history is available", done: sessions.length > 0, tab: "sessions" },
    ];
  }, [credentials.length, documents.length, sessions.length, workspace]);

  const selectedReport = useMemo<SessionReport | null>(() => {
    if (!workspace) return null;
    const session = sessions.find((item) => item.id === selectedSessionId);
    if (!session) return null;
    return {
      session,
      summary: sessionSummaries[session.id] ?? null,
      workspaceId: workspace.id,
      workspaceName: workspace.name,
    };
  }, [selectedSessionId, sessionSummaries, sessions, workspace]);

  if (!workspace) {
    return (
      <AdminShell title="Product" description="Loading product configuration..." actions={<Link href="/admin/products" className="btn-secondary">Back to products</Link>}>
        <p className="text-sm text-[var(--text-secondary)]">Loading product workspace...</p>
      </AdminShell>
    );
  }

  return (
    <AdminShell
      title={workspace.name}
      description="Legacy workspace data is organized here in the new product-first admin structure."
      actions={
        <>
          <a href={demoLink} target="_blank" rel="noreferrer" className="btn-secondary">Open demo</a>
          <Link href="/admin/products" className="btn-secondary">Back to products</Link>
        </>
      }
    >
      <div className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.82)] px-2 py-2">
        <div className="flex flex-wrap gap-1.5">
          {TABS.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} className="admin-segment" data-active={activeTab === tab.key ? "true" : "false"}>{tab.label}</button>
          ))}
        </div>
      </div>

      {activeTab === "overview" ? (
        <div className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_360px]">
            <form onSubmit={saveOverview} className="admin-panel rounded-[24px] px-5 py-5">
              <p className="admin-eyebrow">Product identity</p>
              <h2 className="mt-2 text-[1.8rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Overview</h2>
              <div className="mt-5 grid gap-4">
                <div><label className="mb-2 block text-sm text-[var(--text-primary)]">Product name</label><input className="input" value={workspace.name} onChange={(event) => setWorkspace({ ...workspace, name: event.target.value })} /></div>
                <div><label className="mb-2 block text-sm text-[var(--text-primary)]">Website URL</label><input className="input" value={workspace.product_url || ""} onChange={(event) => setWorkspace({ ...workspace, product_url: event.target.value })} /></div>
                <div><label className="mb-2 block text-sm text-[var(--text-primary)]">Description</label><textarea className="textarea" rows={3} value={workspace.description || ""} onChange={(event) => setWorkspace({ ...workspace, description: event.target.value })} /></div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div><label className="mb-2 block text-sm text-[var(--text-primary)]">Allowed domains</label><input className="input" value={workspace.allowed_domains} onChange={(event) => setWorkspace({ ...workspace, allowed_domains: event.target.value })} /></div>
                  <div><label className="mb-2 block text-sm text-[var(--text-primary)]">Access type</label><select className="input" value={workspace.browser_auth_mode} onChange={(event) => setWorkspace({ ...workspace, browser_auth_mode: event.target.value })}><option value="credentials">Login with credentials</option><option value="none">Public URL</option></select></div>
                </div>
              </div>
              <div className="mt-5 flex justify-end"><button type="submit" className="btn-primary">Save changes</button></div>
            </form>

            <div className="space-y-4">
              <div className="admin-panel rounded-[24px] px-5 py-5">
                <p className="admin-eyebrow">Setup</p>
                <h2 className="mt-2 text-[1.45rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Readiness</h2>
                <div className="mt-4 space-y-3">
                  {checklist.map((item) => (
                    <button key={item.label} type="button" onClick={() => setActiveTab(item.tab as any)} className="flex w-full items-center justify-between rounded-[18px] border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-3 text-left">
                      <span className="text-sm text-[var(--text-primary)]">{item.done ? "✓" : "○"} {item.label}</span>
                      <span className="text-xs uppercase tracking-[0.14em] text-[var(--text-tertiary)]">{item.tab}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="admin-panel rounded-[24px] px-5 py-5">
                <p className="admin-eyebrow">Quick stats</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <div><p className="text-[1.6rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">{documents.length}</p><p className="mt-1 text-sm text-[var(--text-secondary)]">Knowledge entries</p></div>
                  <div><p className="text-[1.6rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">{recipes.length}</p><p className="mt-1 text-sm text-[var(--text-secondary)]">Recipes</p></div>
                  <div><p className="text-[1.6rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">{sessions.length}</p><p className="mt-1 text-sm text-[var(--text-secondary)]">Sessions</p></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === "knowledge" ? (
        <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
          <div className="admin-panel rounded-[24px] px-4 py-4">
            <p className="admin-eyebrow">Knowledge</p>
            <h2 className="mt-2 text-[1.35rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">All sources</h2>
            <div className="mt-4 space-y-2">
              {documents.map((doc) => (
                <div key={doc.id} className="rounded-[18px] border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-3">
                  <p className="text-sm text-[var(--text-primary)]">{doc.filename}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.14em] text-[var(--text-tertiary)]">{doc.file_type} · {doc.status}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-4">
            <form onSubmit={uploadDocument} className="admin-panel rounded-[24px] px-5 py-5">
              <p className="admin-eyebrow">Add source</p>
              <h2 className="mt-2 text-[1.45rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Paste a document or manual note</h2>
              <div className="mt-5 grid gap-4">
                <input className="input" placeholder="Filename or source title" value={docForm.filename} onChange={(event) => setDocForm({ ...docForm, filename: event.target.value })} required />
                <select className="input" value={docForm.file_type} onChange={(event) => setDocForm({ ...docForm, file_type: event.target.value })}>
                  <option value="md">Web page / markdown</option>
                  <option value="txt">Plain text</option>
                  <option value="manual_note">Manual note</option>
                </select>
                <textarea className="textarea" rows={8} placeholder="Paste the product explanation, help page, or manual note here..." value={docForm.content_text} onChange={(event) => setDocForm({ ...docForm, content_text: event.target.value })} required />
              </div>
              <div className="mt-5 flex justify-end"><button type="submit" className="btn-primary">Upload & ingest</button></div>
            </form>
          </div>
        </div>
      ) : null}

      {activeTab === "agent" ? (
        <div className="space-y-4">
          <div className="admin-panel rounded-[24px] px-5 py-5">
            <p className="admin-eyebrow">Compatibility note</p>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">This legacy stack uses credentials, demo recipes, and policy rules instead of the richer persona model in the newer admin.</p>
          </div>
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <form onSubmit={addCredential} className="admin-panel rounded-[24px] px-5 py-5">
              <p className="admin-eyebrow">Demo connection</p>
              <h2 className="mt-2 text-[1.45rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Credentials</h2>
              <div className="mt-5 grid gap-4">
                <input className="input" placeholder="Label" value={credForm.label} onChange={(event) => setCredForm({ ...credForm, label: event.target.value })} required />
                <input className="input" placeholder="Login URL" value={credForm.login_url} onChange={(event) => setCredForm({ ...credForm, login_url: event.target.value })} required />
                <div className="grid gap-4 md:grid-cols-2">
                  <input className="input" placeholder="Username / email" value={credForm.username} onChange={(event) => setCredForm({ ...credForm, username: event.target.value })} required />
                  <input className="input" type="password" placeholder="Password" value={credForm.password} onChange={(event) => setCredForm({ ...credForm, password: event.target.value })} required />
                </div>
              </div>
              <div className="mt-5 flex justify-end"><button type="submit" className="btn-primary">Add credential</button></div>
            </form>

            <form onSubmit={addPolicy} className="admin-panel rounded-[24px] px-5 py-5">
              <p className="admin-eyebrow">Guardrails</p>
              <h2 className="mt-2 text-[1.45rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Policies</h2>
              <div className="mt-5 grid gap-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <select className="input" value={policyForm.rule_type} onChange={(event) => setPolicyForm({ ...policyForm, rule_type: event.target.value })}><option value="blocked_topic">Blocked topic</option><option value="blocked_action">Blocked action</option><option value="escalation_condition">Escalation condition</option><option value="allowed_route">Allowed route</option><option value="blocked_route">Blocked route</option></select>
                  <select className="input" value={policyForm.action} onChange={(event) => setPolicyForm({ ...policyForm, action: event.target.value })}><option value="refuse">Refuse</option><option value="escalate">Escalate</option><option value="warn">Warn</option></select>
                  <select className="input" value={policyForm.severity} onChange={(event) => setPolicyForm({ ...policyForm, severity: event.target.value })}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
                </div>
                <input className="input" placeholder="Pattern" value={policyForm.pattern} onChange={(event) => setPolicyForm({ ...policyForm, pattern: event.target.value })} required />
                <input className="input" placeholder="Description" value={policyForm.description} onChange={(event) => setPolicyForm({ ...policyForm, description: event.target.value })} />
              </div>
              <div className="mt-5 flex justify-end"><button type="submit" className="btn-primary">Add policy</button></div>
            </form>
          </div>

          <form onSubmit={addRecipe} className="admin-panel rounded-[24px] px-5 py-5">
            <p className="admin-eyebrow">Walkthroughs</p>
            <h2 className="mt-2 text-[1.45rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Recipes</h2>
            <div className="mt-5 grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <input className="input" placeholder="Recipe name" value={recipeForm.name} onChange={(event) => setRecipeForm({ ...recipeForm, name: event.target.value })} required />
                <input className="input" type="number" placeholder="Priority" value={recipeForm.priority} onChange={(event) => setRecipeForm({ ...recipeForm, priority: Number(event.target.value) || 0 })} />
              </div>
              <input className="input" placeholder="Description" value={recipeForm.description} onChange={(event) => setRecipeForm({ ...recipeForm, description: event.target.value })} />
              <input className="input" placeholder="Trigger phrases" value={recipeForm.trigger_phrases} onChange={(event) => setRecipeForm({ ...recipeForm, trigger_phrases: event.target.value })} />
              <textarea className="textarea font-mono text-sm" rows={6} placeholder='[{"action":"navigate","target":"https://app.example.com"}]' value={recipeForm.steps_json} onChange={(event) => setRecipeForm({ ...recipeForm, steps_json: event.target.value })} required />
            </div>
            <div className="mt-5 flex justify-end"><button type="submit" className="btn-primary">Create recipe</button></div>
          </form>
        </div>
      ) : null}

      {activeTab === "sessions" ? (
        <div className="space-y-4">
          <div className="admin-panel rounded-[16px] px-5 py-5">
            <p className="admin-eyebrow">Sessions</p>
            <div className="mt-5 overflow-hidden rounded-[12px] border border-[var(--border-subtle)]">
              <div className="hidden grid-cols-[180px_minmax(0,1fr)_110px_110px_90px] gap-4 bg-[var(--surface-muted)] px-4 py-3 text-xs uppercase tracking-[0.08em] text-[var(--text-tertiary)] md:grid">
                <span>Date</span>
                <span>Prospect</span>
                <span>Duration</span>
                <span>Questions</span>
                <span>Handoff</span>
              </div>
              {sessions.map((session) => {
                const report: SessionReport = {
                  session,
                  summary: sessionSummaries[session.id] ?? null,
                  workspaceId: workspace.id,
                  workspaceName: workspace.name,
                };
                return (
                  <button key={session.id} type="button" onClick={() => setSelectedSessionId(session.id)} className="admin-table-row w-full px-4 py-4 text-left">
                    <div className="grid gap-3 md:grid-cols-[180px_minmax(0,1fr)_110px_110px_90px] md:items-center md:gap-4">
                      <p className="text-sm text-[var(--text-secondary)]">{formatDate(session.started_at)}</p>
                      <div>
                        <p className="text-sm text-[var(--text-primary)]">{session.buyer_name || "Anonymous prospect"}</p>
                        <p className="mt-1 text-sm text-[var(--text-secondary)]">{report.summary?.summary_text || "No summary available."}</p>
                      </div>
                      <p className="text-sm text-[var(--text-secondary)]">{formatDuration(report.summary?.duration_seconds)}</p>
                      <p className="text-sm text-[var(--text-secondary)]">{questionCount(report)}</p>
                      <p className="text-sm text-[var(--text-secondary)]">{escalationReasonsForReport(report).length > 0 ? "Yes" : "No"}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
          {selectedReport ? (
            <SessionReportDetail report={selectedReport} messages={sessionMessages} actions={sessionActions} />
          ) : (
            <div className="admin-empty px-6 py-14 text-center text-sm text-[var(--text-secondary)]">Select a session to inspect the full report.</div>
          )}
        </div>
      ) : null}

      {activeTab === "share" ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="admin-panel rounded-[24px] px-5 py-5">
            <p className="admin-eyebrow">Share</p>
            <h2 className="mt-2 text-[1.45rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Launch surface</h2>
            <div className="mt-5 space-y-4">
              <div><label className="mb-2 block text-sm text-[var(--text-primary)]">Demo link</label><code className="admin-code">{demoLink}</code></div>
              <div><label className="mb-2 block text-sm text-[var(--text-primary)]">Live meeting link</label><code className="admin-code">{liveLink}</code></div>
              <div><label className="mb-2 block text-sm text-[var(--text-primary)]">Embed code</label><textarea className="textarea font-mono text-sm" rows={4} readOnly value={embedCode} /></div>
            </div>
          </div>
          <div className="admin-panel rounded-[24px] px-5 py-5">
            <p className="admin-eyebrow">Scope</p>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">Starter questions, brand overrides, and post-session CTAs are part of the newer admin stack. In demobase this tab focuses on the share links generated from the public token.</p>
          </div>
        </div>
      ) : null}
    </AdminShell>
  );
}
