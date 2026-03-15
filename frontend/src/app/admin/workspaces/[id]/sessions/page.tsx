"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

export default function SessionsPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const wsId = params?.id ?? "";
  const sessionId = searchParams?.get("session") ?? null;

  const [sessions, setSessions] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);

  useEffect(() => {
    api.getWorkspaceSessions(wsId).then(setSessions);
  }, [wsId]);

  useEffect(() => {
    if (sessionId) {
      loadSessionDetail(sessionId);
    }
  }, [sessionId]);

  async function loadSessionDetail(sid: string) {
    try {
      const [session, msgs, acts] = await Promise.all([
        api.getSession(sid),
        api.getMessages(sid),
        api.getSessionActions(sid),
      ]);
      setSelectedSession(session);
      setMessages(msgs);
      setActions(acts);
      try {
        const sum = await api.getSessionSummary(sid);
        setSummary(sum);
      } catch {
        setSummary(null);
      }
    } catch (e) {
      console.error("Failed to load session:", e);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <Link href={`/admin/workspaces/${wsId}`} className="text-sm text-gray-500 hover:text-gray-700">
            &larr; Back to Workspace
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">Session History</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-3 gap-6">
        {/* Session List */}
        <div className="col-span-1 space-y-2">
          {sessions.map((s: any) => (
            <button
              key={s.id}
              onClick={() => loadSessionDetail(s.id)}
              className={`card w-full text-left py-3 hover:shadow-md transition-shadow ${
                selectedSession?.id === s.id ? "ring-2 ring-primary-500" : ""
              }`}
            >
              <p className="font-medium text-sm">{s.buyer_name || "Anonymous"}</p>
              <p className="text-xs text-gray-400">
                {new Date(s.started_at).toLocaleString()}
              </p>
              <div className="flex gap-2 mt-1">
                <span className={s.status === "active" ? "badge-green" : "badge-blue"}>
                  {s.status}
                </span>
                {s.lead_intent_score != null && (
                  <span className="badge-yellow">Score: {s.lead_intent_score}</span>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Session Detail */}
        <div className="col-span-2">
          {selectedSession ? (
            <div className="space-y-6">
              {/* Summary Card */}
              {summary && (
                <div className="card">
                  <h3 className="font-semibold mb-3">Session Summary</h3>
                  <p className="text-sm text-gray-700 mb-3">{summary.summary_text}</p>
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-primary-600">{summary.lead_intent_score}</p>
                      <p className="text-xs text-gray-500">Intent Score</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-gray-700">{summary.total_messages}</p>
                      <p className="text-xs text-gray-500">Messages</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-gray-700">{summary.total_actions}</p>
                      <p className="text-xs text-gray-500">Actions</p>
                    </div>
                  </div>
                  {summary.top_questions && (
                    <div className="mb-2">
                      <p className="text-xs font-medium text-gray-500 mb-1">Top Questions</p>
                      <ul className="text-sm text-gray-600 space-y-1">
                        {JSON.parse(summary.top_questions).slice(0, 5).map((q: string, i: number) => (
                          <li key={i} className="truncate">&bull; {q}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Transcript */}
              <div className="card">
                <h3 className="font-semibold mb-3">Transcript</h3>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {messages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[80%] px-4 py-2 rounded-xl text-sm ${
                        msg.role === "user"
                          ? "bg-primary-600 text-white"
                          : msg.role === "system"
                          ? "bg-gray-200 text-gray-600 italic"
                          : "bg-gray-100 text-gray-800"
                      }`}>
                        {msg.planner_decision && (
                          <span className="text-xs opacity-70 block mb-1">[{msg.planner_decision}]</span>
                        )}
                        {msg.content}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Browser Actions */}
              {actions.length > 0 && (
                <div className="card">
                  <h3 className="font-semibold mb-3">Browser Audit Trail ({actions.length} actions)</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {actions.map((a: any) => (
                      <div key={a.id} className="flex items-center gap-3 text-sm">
                        <span className={`w-2 h-2 rounded-full ${a.status === "success" ? "bg-green-500" : "bg-red-500"}`} />
                        <span className="font-mono text-xs text-gray-500">{a.action_type}</span>
                        <span className="text-gray-600 truncate">{a.narration || a.target || ""}</span>
                        {a.duration_ms && <span className="text-xs text-gray-400">{a.duration_ms}ms</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card text-center py-12 text-gray-500">
              Select a session to view details
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
