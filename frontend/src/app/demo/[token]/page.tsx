"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";

import { api } from "@/lib/api";
import type { AgentStatus, DemoSession, LiveStartResponse, SessionMessage } from "@/types/api";

const STATUS_LABELS: Record<AgentStatus, string> = {
  idle: "Ready",
  thinking: "Thinking...",
  checking_docs: "Checking documentation...",
  navigating: "Navigating...",
  showing_feature: "Showing feature...",
  escalated: "Connecting to sales team...",
  error: "Something went wrong",
};

function normalizeSession(session: any): DemoSession {
  return {
    ...session,
    live_status: session.live_status ?? "idle",
    active_recipe_id: session.active_recipe_id ?? null,
    current_step_index: session.current_step_index ?? 0,
    live_room_name: session.live_room_name ?? null,
  };
}

export default function DemoPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";

  const [session, setSession] = useState<DemoSession | null>(null);
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [liveInfo, setLiveInfo] = useState<LiveStartResponse | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [summaryNote, setSummaryNote] = useState<string | null>(null);
  const [showIntro, setShowIntro] = useState(true);
  const [buyerName, setBuyerName] = useState("");
  const [buyerEmail, setBuyerEmail] = useState("");
  const [browserTrackReady, setBrowserTrackReady] = useState(false);
  const [audioReady, setAudioReady] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const browserContainerRef = useRef<HTMLDivElement>(null);
  const audioContainerRef = useRef<HTMLDivElement>(null);
  const roomRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const closingLiveRef = useRef(false);

  const isEnded = session?.status === "ended";
  const liveStatus = session?.live_status ?? "idle";
  const liveActive = Boolean(liveInfo);
  const liveStatusLabel = useMemo(() => {
    if (!liveActive) return null;
    if (liveStatus === "starting") return "Connecting live session...";
    if (liveStatus === "paused") return "Live demo paused";
    if (liveStatus === "error") return "Live demo error";
    if (liveStatus === "ended") return "Live demo ended";
    return browserTrackReady ? "Watching the live product session" : "Waiting for live product video...";
  }, [browserTrackReady, liveActive, liveStatus]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => {
      void disconnectLiveSession();
    };
  }, []);

  async function disconnectLiveSession() {
    closingLiveRef.current = true;
    wsRef.current?.close();
    wsRef.current = null;

    if (roomRef.current) {
      await roomRef.current.disconnect();
      roomRef.current = null;
    }

    if (browserContainerRef.current) {
      browserContainerRef.current.innerHTML = "";
    }
    if (audioContainerRef.current) {
      audioContainerRef.current.innerHTML = "";
    }

    setBrowserTrackReady(false);
    setAudioReady(false);
    setLiveInfo(null);
  }

  function appendMessage(message: SessionMessage) {
    setMessages((prev) => {
      const exists = prev.some(
        (item) =>
          item.role === message.role &&
          item.content === message.content &&
          item.message_type === message.message_type,
      );
      if (exists) return prev;
      return [...prev, message];
    });
  }

  function appendSystemMessage(content: string) {
    appendMessage({
      id: `system-${Date.now()}`,
      session_id: session?.id ?? "unknown",
      role: "system",
      content,
      message_type: "text",
      planner_decision: null,
      created_at: new Date().toISOString(),
    });
  }

  function handleLiveEvent(event: any) {
    if (event.type === "connected") {
      return;
    }

    if (event.type === "status") {
      setSession((prev) => (prev ? { ...prev, live_status: event.live_status ?? prev.live_status, current_step_index: event.current_step_index ?? prev.current_step_index } : prev));
      if (event.live_status === "paused") {
        setStatus("idle");
      }
      if (event.live_status === "error") {
        setStatus("error");
      }
      return;
    }

    if (event.type === "transcript") {
      appendMessage({
        id: `${event.role}-${event.timestamp}`,
        session_id: session?.id ?? "unknown",
        role: event.role,
        content: event.content,
        message_type: event.message_type ?? "text",
        planner_decision: event.planner_decision ?? null,
        created_at: event.timestamp,
      });
      return;
    }

    if (event.type === "recipe_started") {
      setStatus("showing_feature");
      appendSystemMessage(`Starting demo flow: ${event.recipe_name}`);
      return;
    }

    if (event.type === "recipe_step") {
      setSession((prev) => (prev ? { ...prev, current_step_index: event.step_index ?? prev.current_step_index } : prev));
      setStatus(event.success ? "showing_feature" : "error");
      if (event.narration) {
        appendSystemMessage(event.narration);
      }
      return;
    }

    if (event.type === "recipe_completed") {
      setStatus("idle");
      appendSystemMessage(`Completed demo flow: ${event.recipe_name}`);
      return;
    }

    if (event.type === "runtime_error") {
      setStatus("error");
      setLiveError(event.detail || "Live demo error");
      appendSystemMessage(event.detail || "Live demo encountered an error.");
      return;
    }

    if (event.type === "session_ended") {
      setStatus("idle");
      setSession((prev) => (prev ? { ...prev, status: "ended", live_status: "ended" } : prev));
      if (event.summary_text) {
        setSummaryNote(event.summary_text);
      }
    }
  }

  async function connectRoom(live: LiveStartResponse) {
    const livekit = await import("livekit-client");
    const room = new livekit.Room();
    roomRef.current = room;

    room.on(livekit.RoomEvent.TrackSubscribed, (track: any, publication: any) => {
      const element = track.attach();
      element.className = "h-full w-full";

      if (publication.trackName === "browser-video") {
        if (browserContainerRef.current) {
          browserContainerRef.current.innerHTML = "";
          browserContainerRef.current.appendChild(element);
        }
        setBrowserTrackReady(true);
        return;
      }

      if (publication.trackName === "agent-audio") {
        if (audioContainerRef.current) {
          audioContainerRef.current.innerHTML = "";
          audioContainerRef.current.appendChild(element);
        }
        setAudioReady(true);
      }
    });

    room.on(livekit.RoomEvent.TrackUnsubscribed, (track: any) => {
      track.detach().forEach((element: HTMLElement) => element.remove());
    });

    await room.connect(live.livekit_url!, live.participant_token!);

    try {
      await room.localParticipant.setMicrophoneEnabled(true);
    } catch {
      appendSystemMessage("Microphone access was denied. Text chat is still available.");
    }
  }

  function connectEvents(live: LiveStartResponse) {
    if (!live.event_ws_url) return;
    const socket = new WebSocket(live.event_ws_url);
    socket.onmessage = (event) => {
      try {
        handleLiveEvent(JSON.parse(event.data));
      } catch {
        // Ignore malformed events.
      }
    };
    socket.onclose = () => {
      if (!closingLiveRef.current) {
        setLiveError("Live event connection closed.");
      }
    };
    wsRef.current = socket;
  }

  async function startSession() {
    try {
      const created = normalizeSession(
        await api.createSession({
          public_token: token,
          buyer_name: buyerName || undefined,
          buyer_email: buyerEmail || undefined,
          mode: "text",
        }),
      );
      setSession(created);
      setShowIntro(false);
      setSummaryNote(null);
      setLiveError(null);
      setMessages(await api.getMessages(created.id));
    } catch (e: any) {
      setLiveError(e.message || "Failed to start session. Check that the demo link is valid.");
    }
  }

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !session || status !== "idle") return;

    const userMsg = input.trim();
    setInput("");
    appendMessage({
      id: `temp-${Date.now()}`,
      session_id: session.id,
      role: "user",
      content: userMsg,
      message_type: "text",
      planner_decision: null,
      created_at: new Date().toISOString(),
    });
    setStatus("thinking");

    try {
      const agentMsg = await api.sendMessage(session.id, userMsg);
      setMessages((prev) => {
        const filtered = prev.filter((m) => !m.id.startsWith("temp-"));
        return [
          ...filtered,
          {
            id: `user-${Date.now()}`,
            session_id: session.id,
            role: "user",
            content: userMsg,
            message_type: "text",
            planner_decision: null,
            created_at: new Date().toISOString(),
          },
          agentMsg,
        ];
      });

      if (agentMsg.planner_decision === "answer_and_demo" && liveActive) {
        setStatus("showing_feature");
        return;
      }
      if (agentMsg.planner_decision === "escalate") {
        setStatus("escalated");
        setTimeout(() => setStatus("idle"), 3000);
        return;
      }
      setStatus("idle");
    } catch (e: any) {
      setStatus("error");
      appendSystemMessage(e.message || "Failed to get response. Please try again.");
      setTimeout(() => setStatus("idle"), 2000);
    }
  }

  async function handleStartLiveDemo() {
    if (!session) return;
    setStatus("navigating");
    setLiveError(null);
    closingLiveRef.current = false;

    try {
      const live = await api.startLive(session.id);
      const capabilities = JSON.parse(live.capabilities_json || "{}");
      if (!capabilities.mock_media && live.livekit_url && live.participant_token) {
        await connectRoom(live);
      } else {
        setBrowserTrackReady(true);
        setAudioReady(Boolean(capabilities.voice));
      }
      connectEvents(live);
      setLiveInfo(live);
      setSession((prev) => (prev ? { ...prev, mode: "live", live_status: "live", live_room_name: live.room_name } : prev));
      setStatus("idle");
    } catch (e: any) {
      setStatus("error");
      setLiveError(e.message || "Could not start the live demo.");
      appendSystemMessage(`Live demo: ${e.message || "Could not start the live browser session."}`);
      setTimeout(() => setStatus("idle"), 2000);
    }
  }

  async function handleControl(action: "pause" | "resume" | "next-step" | "restart") {
    if (!session) return;
    try {
      const response =
        action === "pause"
          ? await api.pauseLive(session.id)
          : action === "resume"
          ? await api.resumeLive(session.id)
          : action === "next-step"
          ? await api.nextLiveStep(session.id)
          : await api.restartLive(session.id);

      setSession((prev) =>
        prev
          ? {
              ...prev,
              live_status: response.live_status,
              active_recipe_id: response.active_recipe_id,
              current_step_index: response.current_step_index,
            }
          : prev,
      );
      if (response.detail) {
        appendSystemMessage(response.detail);
      }
    } catch (e: any) {
      setLiveError(e.message || "Could not send live control.");
    }
  }

  async function handleEndSession() {
    if (!session) return;
    try {
      const result = await api.endSession(session.id);
      setSummaryNote(result.summary?.summary_text || null);
      appendSystemMessage(`Session ended. Lead intent score: ${result.summary?.lead_intent_score || "N/A"}`);
      setSession({ ...session, status: "ended", live_status: "ended" });
      await disconnectLiveSession();
    } catch (e: any) {
      setLiveError(e.message || "Failed to end the session.");
    }
  }

  if (showIntro) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 to-blue-100 flex items-center justify-center">
        <div className="card max-w-md w-full mx-4">
          <h1 className="text-2xl font-bold text-center mb-2">Product Demo</h1>
          <p className="text-gray-500 text-center mb-6 text-sm">
            Chat with the agent, then switch into the live product session when you want a real walkthrough.
          </p>
          {liveError && (
            <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{liveError}</div>
          )}
          <div className="space-y-3">
            <input
              className="input"
              placeholder="Your name (optional)"
              value={buyerName}
              onChange={(e) => setBuyerName(e.target.value)}
            />
            <input
              className="input"
              placeholder="Your email (optional)"
              value={buyerEmail}
              onChange={(e) => setBuyerEmail(e.target.value)}
            />
            <button onClick={startSession} className="btn-primary w-full py-3 text-lg">
              Start Demo
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-gray-900">Live Demo</h1>
          <p className="text-xs text-gray-400">
            {status !== "idle" && (
              <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                {STATUS_LABELS[status]}
              </span>
            )}
            {status === "idle" && liveStatusLabel && (
              <span className="inline-flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${browserTrackReady ? "bg-green-500" : "bg-yellow-500"}`} />
                {liveStatusLabel}
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          {!liveActive && !isEnded && (
            <button onClick={handleStartLiveDemo} className="btn-secondary text-sm">
              Start Live Demo
            </button>
          )}
          {!isEnded && (
            <button onClick={handleEndSession} className="btn-secondary text-sm text-red-600 border-red-200">
              End Session
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className={`flex flex-col ${liveActive ? "w-5/12" : "w-full max-w-3xl mx-auto"}`}>
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-primary-600 text-white rounded-br-md"
                      : msg.role === "system"
                      ? "bg-yellow-50 text-yellow-800 border border-yellow-200 rounded-bl-md"
                      : "bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-md"
                  }`}
                >
                  {msg.role === "agent" && msg.planner_decision && (
                    <span className="text-xs text-gray-400 block mb-1">
                      {msg.planner_decision === "answer_and_demo" && "Answering + showing demo"}
                      {msg.planner_decision === "answer_only" && "From docs or live product"}
                      {msg.planner_decision === "escalate" && "Escalated to sales team"}
                      {msg.planner_decision === "refuse" && "Not available in demo"}
                      {msg.planner_decision === "clarify" && "Needs clarification"}
                    </span>
                  )}
                  {msg.content}
                </div>
              </div>
            ))}
            {summaryNote && (
              <div className="rounded-2xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-900">
                {summaryNote}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {!isEnded && (
            <form onSubmit={sendMessage} className="border-t border-gray-200 bg-white p-4">
              <div className="flex gap-2">
                <input
                  className="input flex-1"
                  placeholder={status === "idle" ? "Ask about the product..." : STATUS_LABELS[status]}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={status !== "idle"}
                  autoFocus
                />
                <button
                  type="submit"
                  disabled={!input.trim() || status !== "idle"}
                  className="btn-primary"
                >
                  Send
                </button>
              </div>
              <div className="flex gap-3 mt-2 flex-wrap">
                {[
                  "Show me the sequence dashboard",
                  "Walk me through analytics reports",
                  "Can I get annual discount pricing?",
                ].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setInput(q)}
                    className="text-xs text-primary-600 hover:underline"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </form>
          )}
        </div>

        {liveActive && (
          <div className="w-7/12 border-l border-gray-200 bg-gray-950 flex flex-col">
            <div className="bg-gray-900 px-4 py-3 flex flex-wrap items-center gap-2 text-xs text-gray-300">
              <span className="font-semibold text-white">Live Product Session</span>
              <span className="rounded-full border border-gray-700 px-2 py-1">
                {browserTrackReady ? "Video connected" : "Waiting for browser video"}
              </span>
              <span className="rounded-full border border-gray-700 px-2 py-1">
                {audioReady ? "Agent audio live" : "Audio pending"}
              </span>
              <span className="rounded-full border border-gray-700 px-2 py-1">
                Step {session?.current_step_index ?? 0}
              </span>
              <div className="ml-auto flex gap-2">
                <button onClick={() => handleControl("pause")} className="btn-secondary text-xs">
                  Pause
                </button>
                <button onClick={() => handleControl("resume")} className="btn-secondary text-xs">
                  Resume
                </button>
                <button onClick={() => handleControl("next-step")} className="btn-secondary text-xs">
                  Next Step
                </button>
                <button onClick={() => handleControl("restart")} className="btn-secondary text-xs">
                  Restart Demo
                </button>
              </div>
            </div>
            <div className="relative flex-1 overflow-hidden">
              <div ref={browserContainerRef} className="h-full w-full [&>video]:h-full [&>video]:w-full [&>video]:object-contain" />
              {!browserTrackReady && (
                <div className="absolute inset-0 flex items-center justify-center text-center text-gray-400">
                  <div>
                    <p className="text-lg mb-2">Connecting to the real product session</p>
                    <p className="text-sm">The agent is preparing the live browser and joining the room.</p>
                  </div>
                </div>
              )}
            </div>
            <div ref={audioContainerRef} className="hidden" />
            {liveError && (
              <div className="border-t border-red-900 bg-red-950/60 px-4 py-3 text-sm text-red-200">
                {liveError}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
