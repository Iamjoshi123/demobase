"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";

import { apiV2 } from "@/lib/api-v2";
import type {
  MeetingBrowserPlanV2,
  MeetingLiveStartV2,
  MeetingMessageV2,
  MeetingSessionV2,
  MeetingTurnV2,
} from "@/types/v2";

type ParsedMetadata = Record<string, unknown>;
type SetupPhase = "creating" | "voice" | "browser" | "live" | "ready" | "failed";
type BrowserStageState = "attaching" | "live" | "black_frames" | "errored";

const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "pt", label: "Portuguese" },
  { value: "ja", label: "Japanese" },
] as const;

function parsePreferredLanguage(source: string | null | undefined): string {
  const metadata = parseMetadata(source);
  const preferred = metadata.preferred_language;
  return typeof preferred === "string" && preferred.trim() ? preferred.trim().toLowerCase() : "en";
}

function parseActions(message: MeetingMessageV2): string[] {
  try {
    return JSON.parse(message.next_actions_json || "[]");
  } catch {
    return [];
  }
}

function parseCapabilities(source: string | null | undefined): Record<string, unknown> {
  try {
    return JSON.parse(source || "{}");
  } catch {
    return {};
  }
}

function parseMetadata(source: string | null | undefined): ParsedMetadata {
  try {
    return JSON.parse(source || "{}");
  } catch {
    return {};
  }
}

function summarizeAction(action: string): string {
  if (action.startsWith("run_browser_instruction:")) return "Live browser action";
  if (action.startsWith("fallback_recipe:")) return "Structured fallback";
  if (action.startsWith("launch_recipe:")) return "Structured walkthrough";
  return action.replaceAll("_", " ");
}

function summarizeStrategy(strategy: string | null | undefined): string {
  if (!strategy) return "Agent is reasoning about the next move.";
  if (strategy === "stagehand_then_recipe") return "Agent will try a live browser action, then fall back to a structured walkthrough if needed.";
  if (strategy === "stagehand_only") return "Agent will act directly in the live browser.";
  if (strategy === "recipe_only") return "Agent will use a structured walkthrough.";
  if (strategy === "answer_only") return "Agent will answer first and keep the browser ready.";
  return strategy.replaceAll("_", " ");
}

function describeTurn(turn: MeetingTurnV2): string {
  if (turn.browser_instruction) {
    return "Trying a direct browser action in the live product.";
  }
  if (turn.recipe_id) {
    return "Using a structured walkthrough for this request.";
  }
  if (turn.policy_decision === "escalate") {
    return "Keeping the demo safe and escalating the commercial question.";
  }
  return summarizeStrategy(turn.action_strategy);
}

async function videoLooksBlack(video: HTMLVideoElement): Promise<boolean> {
  return (await sampleVideoBrightness(video)) < 6;
}

async function sampleVideoBrightness(video: HTMLVideoElement): Promise<number> {
  if (video.videoWidth === 0 || video.videoHeight === 0) return 0;
  const canvas = document.createElement("canvas");
  canvas.width = 24;
  canvas.height = 24;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return 255;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
  let total = 0;
  for (let index = 0; index < data.length; index += 4) {
    total += data[index] + data[index + 1] + data[index + 2];
  }
  return total / (data.length / 4) / 3;
}

function sampleCanvasBrightness(canvas: HTMLCanvasElement): number {
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return 255;
  const sampleCanvas = document.createElement("canvas");
  sampleCanvas.width = 24;
  sampleCanvas.height = 24;
  const sampleContext = sampleCanvas.getContext("2d", { willReadFrequently: true });
  if (!sampleContext) return 255;
  sampleContext.drawImage(canvas, 0, 0, sampleCanvas.width, sampleCanvas.height);
  const { data } = sampleContext.getImageData(0, 0, sampleCanvas.width, sampleCanvas.height);
  let total = 0;
  for (let index = 0; index < data.length; index += 4) {
    total += data[index] + data[index + 1] + data[index + 2];
  }
  return total / (data.length / 4) / 3;
}

async function waitForHealthyVideo(video: HTMLVideoElement, attempts = 5, delayMs = 500): Promise<boolean> {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      if (!(await videoLooksBlack(video))) {
        return true;
      }
    } catch {
      return false;
    }
    await new Promise((resolve) => window.setTimeout(resolve, delayMs));
  }
  return false;
}

function DemoStageMessage({
  message,
}: {
  message: MeetingMessageV2;
}) {
  const actions = parseActions(message);

  if (message.role === "system") {
    return (
      <div className="rounded-2xl border border-[var(--border-subtle)] bg-[rgba(232,168,76,0.08)] px-4 py-3 text-[13px] leading-6 text-[var(--text-secondary)]">
        {message.content}
      </div>
    );
  }

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[92%] rounded-[22px] bg-[rgba(232,168,76,0.14)] px-4 py-3 text-[15px] leading-7 text-[var(--text-primary)] shadow-[0_10px_28px_rgba(0,0,0,0.16)] ring-1 ring-[var(--border-active)]">
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[94%] rounded-[24px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.035)] px-4 py-4 text-[15px] leading-7 text-[var(--text-primary)] shadow-[0_18px_40px_rgba(0,0,0,0.16)]">
        {message.stage && (
          <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">
            {message.stage}
          </p>
        )}
        <p>{message.content}</p>
        {actions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {actions.map((action) => (
              <span
                key={action}
                className="rounded-full border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.05)] px-3 py-1 text-[11px] uppercase tracking-[0.08em] text-[var(--text-secondary)]"
              >
                {summarizeAction(action)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MeetingPageV2() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";

  const [meeting, setMeeting] = useState<MeetingSessionV2 | null>(null);
  const [messages, setMessages] = useState<MeetingMessageV2[]>([]);
  const [liveInfo, setLiveInfo] = useState<MeetingLiveStartV2 | null>(null);
  const [browserPlan, setBrowserPlan] = useState<MeetingBrowserPlanV2 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [browserTrackReady, setBrowserTrackReady] = useState(false);
  const [browserStageState, setBrowserStageState] = useState<BrowserStageState>("attaching");
  const [audioReady, setAudioReady] = useState(false);
  const [audioUnlockNeeded, setAudioUnlockNeeded] = useState(false);
  const [micReady, setMicReady] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState(() => {
    if (typeof window === "undefined") return "en";
    try {
      return window.localStorage.getItem("demo-preferred-language") || "en";
    } catch {
      return "en";
    }
  });
  const [runtimeNote, setRuntimeNote] = useState("The stage is getting ready.");
  const [setupPhase, setSetupPhase] = useState<SetupPhase>("creating");
  const [setupProgress, setSetupProgress] = useState(8);
  const [setupHeadline, setSetupHeadline] = useState("Your AI demo is getting ready");
  const scrollRef = useRef<HTMLDivElement>(null);
  const browserContainerRef = useRef<HTMLDivElement>(null);
  const browserStageVideoRef = useRef<HTMLVideoElement>(null);
  const browserCanvasRef = useRef<HTMLCanvasElement>(null);
  const audioContainerRef = useRef<HTMLDivElement>(null);
  const browserVideoReadyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const browserVideoElementRef = useRef<HTMLVideoElement | null>(null);
  const browserTrackReadyRef = useRef(false);
  const browserStageStateRef = useRef<BrowserStageState>("attaching");
  const browserRenderFrameRef = useRef<number | null>(null);
  const browserRenderLogCounterRef = useRef(0);
  const browserAttachStartedAtRef = useRef<number | null>(null);
  const roomRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const closingLiveRef = useRef(false);
  const bootstrapStartedRef = useRef(false);

  const latestAgentMessage = useMemo(() => [...messages].reverse().find((message) => message.role === "agent") ?? null, [messages]);
  const latestAgentMetadata = useMemo(() => parseMetadata(latestAgentMessage?.metadata_json), [latestAgentMessage]);

  const workspaceName = useMemo(() => {
    for (const message of messages) {
      const metadata = parseMetadata(message.metadata_json);
      const workspace = metadata.workspace_name;
      if (typeof workspace === "string" && workspace.trim()) {
        return workspace;
      }
    }
    return "DemoAgent";
  }, [messages]);

  const currentFocus = meeting?.current_focus || (typeof latestAgentMetadata.recipe_name === "string" ? latestAgentMetadata.recipe_name : null);
  const userTurnCount = messages.filter((message) => message.role === "user").length;
  const showSuggestedPrompts = userTurnCount === 0;
  const isBootstrapping = setupPhase !== "ready" && setupPhase !== "failed";
  const stageNarrative = useMemo(() => {
    if (liveError) return liveError;
    if (typeof latestAgentMetadata.action_strategy === "string") return summarizeStrategy(latestAgentMetadata.action_strategy);
    return runtimeNote;
  }, [latestAgentMetadata.action_strategy, liveError, runtimeNote]);
  const effectiveBrowserStageState: BrowserStageState = browserTrackReady ? "live" : browserStageState;

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    browserTrackReadyRef.current = browserTrackReady;
  }, [browserTrackReady]);

  useEffect(() => {
    browserStageStateRef.current = browserStageState;
  }, [browserStageState]);

  useEffect(() => {
    return () => {
      void disconnectLiveSession();
    };
  }, []);

  useEffect(() => {
    if (!meeting?.personalization_json) return;
    setSelectedLanguage(parsePreferredLanguage(meeting.personalization_json));
  }, [meeting?.personalization_json]);

  useEffect(() => {
    if (!audioUnlockNeeded) return;

    const unlock = () => {
      void tryStartRoomAudio();
    };

    window.addEventListener("pointerdown", unlock, { passive: true });
    window.addEventListener("keydown", unlock);
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, [audioUnlockNeeded]);

  useEffect(() => {
    if (!token || bootstrapStartedRef.current) return;
    bootstrapStartedRef.current = true;
    void bootstrapMeeting();
    // Setup is intentionally one-shot per token. Re-running it on each helper recreation
    // would tear down the live room and browser while the page is already connected.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function updateSetup(phase: SetupPhase, progress: number, headline: string, detail: string) {
    setSetupPhase(phase);
    setSetupProgress(progress);
    setSetupHeadline(headline);
    setRuntimeNote(detail);
  }

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
    if (browserStageVideoRef.current) {
      browserStageVideoRef.current.pause();
      browserStageVideoRef.current.removeAttribute("src");
      browserStageVideoRef.current.srcObject = null;
    }
    browserVideoElementRef.current = null;
    if (browserRenderFrameRef.current !== null) {
      cancelAnimationFrame(browserRenderFrameRef.current);
      browserRenderFrameRef.current = null;
    }
    if (browserCanvasRef.current) {
      const context = browserCanvasRef.current.getContext("2d");
      context?.clearRect(0, 0, browserCanvasRef.current.width, browserCanvasRef.current.height);
    }
    if (audioContainerRef.current) {
      audioContainerRef.current.innerHTML = "";
    }
    if (browserVideoReadyTimerRef.current) {
      clearTimeout(browserVideoReadyTimerRef.current);
      browserVideoReadyTimerRef.current = null;
    }

    setBrowserTrackReady(false);
    setBrowserStageState("attaching");
    browserAttachStartedAtRef.current = null;
    setAudioReady(false);
    setMicReady(false);
    setLiveInfo(null);
  }

  function appendMessage(message: MeetingMessageV2) {
    setMessages((previous) => {
      const exists = previous.some(
        (item) =>
          item.id === message.id ||
          (item.role === message.role &&
            item.content === message.content &&
            item.message_type === message.message_type &&
            item.created_at === message.created_at),
      );
      if (exists) return previous;
      return [...previous, message];
    });
  }

  function appendSystemMessage(content: string) {
    appendMessage({
      id: `system-${Date.now()}`,
      session_id: meeting?.id ?? "unknown",
      role: "system",
      content,
      message_type: "system",
      stage: meeting?.stage ?? null,
      next_actions_json: "[]",
      metadata_json: null,
      created_at: new Date().toISOString(),
    });
  }

  function stopBrowserCanvasRender() {
    if (browserRenderFrameRef.current !== null) {
      cancelAnimationFrame(browserRenderFrameRef.current);
      browserRenderFrameRef.current = null;
    }
  }

  function renderBrowserVideoToCanvas() {
    const video = browserVideoElementRef.current;
    const canvas = browserCanvasRef.current;
    if (!video || !canvas) return;

    if (video.videoWidth === 0 || video.videoHeight === 0) {
      browserRenderFrameRef.current = requestAnimationFrame(renderBrowserVideoToCanvas);
      return;
    }

    const width = Math.max(video.videoWidth, 1);
    const height = Math.max(video.videoHeight, 1);
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    const context = canvas.getContext("2d", { alpha: false });
    if (!context) return;
    context.drawImage(video, 0, 0, width, height);
    browserRenderLogCounterRef.current += 1;
    const videoAverage = sampleCanvasBrightness(canvas);
    if (videoAverage >= 6 && browserStageStateRef.current !== "live") {
      browserTrackReadyRef.current = true;
      browserStageStateRef.current = "live";
      setBrowserTrackReady(true);
      setBrowserStageState("live");
      setRuntimeNote("Live browser stage is visible.");
      setLiveError(null);
      console.info("[browser-stage] first healthy canvas frame", {
        width,
        height,
        averageBrightness: Number(videoAverage.toFixed(2)),
      });
    } else if (
      videoAverage < 6 &&
      !browserTrackReadyRef.current &&
      browserAttachStartedAtRef.current !== null &&
      performance.now() - browserAttachStartedAtRef.current > 2500 &&
      browserStageStateRef.current !== "black_frames"
    ) {
      browserStageStateRef.current = "black_frames";
      setBrowserStageState("black_frames");
      setRuntimeNote("Browser track is attached, but frames are still rendering black.");
    }
    if (browserRenderLogCounterRef.current <= 3 || browserRenderLogCounterRef.current % 90 === 0) {
      console.info("[browser-stage] canvas frame", {
        frame: browserRenderLogCounterRef.current,
        width,
        height,
        averageBrightness: Number(videoAverage.toFixed(2)),
        readyState: video.readyState,
      });
    }
    browserRenderFrameRef.current = requestAnimationFrame(renderBrowserVideoToCanvas);
  }

  function startBrowserCanvasRender() {
    stopBrowserCanvasRender();
    browserRenderFrameRef.current = requestAnimationFrame(renderBrowserVideoToCanvas);
  }

  async function tryStartRoomAudio() {
    const room = roomRef.current;
    if (!room || typeof room.startAudio !== "function") return;
    try {
      await room.startAudio();
      setAudioUnlockNeeded(false);
      setLiveError((previous) =>
        previous === "Tap or click once to enable agent audio playback." ? null : previous,
      );
      setRuntimeNote((previous) =>
        previous === "Tap or click once to enable agent audio playback."
          ? "Agent audio is enabled."
          : previous,
      );
      console.info("[audio] room audio started");
    } catch (error) {
      console.info("[audio] room audio still locked", error);
      setAudioUnlockNeeded(true);
      setLiveError("Tap or click once to enable agent audio playback.");
      setRuntimeNote("Tap or click once to enable agent audio playback.");
    }
  }

  function handleLiveEvent(event: any) {
    if (event.type === "connected") {
      return;
    }

    if (event.type === "status") {
      setMeeting((previous) =>
        previous
          ? {
              ...previous,
              rtc_status: event.live_status === "live" || event.live_status === "paused" ? "joined" : "ready",
              browser_status: previous.browser_status === "not_started" ? "connected" : previous.browser_status,
              current_step_index: event.current_step_index ?? previous.current_step_index,
            }
          : previous,
      );
      if (event.detail) {
        setRuntimeNote(String(event.detail));
      }
      return;
    }

    if (event.type === "transcript") {
      appendMessage({
        id: `${event.role}-${event.timestamp}`,
        session_id: meeting?.id ?? "unknown",
        role: event.role,
        content: event.content,
        message_type: event.message_type ?? "voice_transcript",
        stage: meeting?.stage ?? null,
        next_actions_json: JSON.stringify(event.next_actions || []),
        metadata_json: JSON.stringify(event.metadata || { planner_decision: event.planner_decision ?? null }),
        created_at: event.timestamp,
      });
      return;
    }

    if (event.type === "voice_state") {
      if (event.detail) {
        setRuntimeNote(String(event.detail));
      }
      return;
    }

    if (event.type === "browser_stage_state") {
      const state = String(event.state || "attaching") as BrowserStageState;
      if (browserTrackReady && state !== "errored") {
        console.info("[browser-stage] ignoring late browser stage state because canvas is already healthy", { state });
        return;
      }
      if (state === "errored") {
        setBrowserTrackReady(false);
        setBrowserStageState("errored");
      } else if (!browserTrackReady) {
        setBrowserStageState(state);
      }
      if (event.detail) {
        setRuntimeNote(String(event.detail));
      }
      if (state === "errored") {
        setLiveError(String(event.detail || "The live browser stage failed."));
      }
      return;
    }

    if (event.type === "startup_state") {
      if (event.detail) {
        setRuntimeNote(String(event.detail));
      }
      if (event.state === "failed") {
        setLiveError(String(event.detail || "Live startup failed."));
      }
      return;
    }

    if (event.type === "browser_action_planned") {
      setMeeting((previous) =>
        previous
          ? {
              ...previous,
              stage: "demo",
              browser_status: "connected",
              current_focus: String(event.focus || previous.current_focus || event.instruction || ""),
            }
          : previous,
      );
      setRuntimeNote("Agent is exploring the live product directly.");
      return;
    }

    if (event.type === "browser_pointer_move" || event.type === "browser_click" || event.type === "browser_scroll" || event.type === "browser_type") {
      return;
    }

    if (event.type === "browser_action_result") {
      setMeeting((previous) =>
        previous
          ? {
              ...previous,
              stage: "demo",
              browser_status: "connected",
              current_focus: String(event.focus || event.page_title || previous.current_focus || ""),
            }
          : previous,
      );
      setRuntimeNote(
        event.success
          ? String(event.page_title || event.narration || "The live browser action completed.")
          : String(event.error || "The direct browser action failed."),
      );
      return;
    }

    if (event.type === "browser_action_verified") {
      setRuntimeNote(String(event.narration || event.page_title || "The browser action completed."));
      return;
    }

    if (event.type === "browser_action_failed") {
      setRuntimeNote(String(event.error || event.narration || "The browser action could not be verified."));
      return;
    }

    if (event.type === "browser_action_fallback") {
      setRuntimeNote(String(event.detail || "The agent is switching to a structured walkthrough."));
      return;
    }

    if (event.type === "recipe_started") {
      setMeeting((previous) =>
        previous
          ? {
              ...previous,
              stage: "demo",
              browser_status: "connected",
              active_recipe_id: event.recipe_id ?? previous.active_recipe_id,
              current_focus: event.recipe_name ?? previous.current_focus,
            }
          : previous,
      );
      setRuntimeNote(`Running structured walkthrough: ${event.recipe_name}`);
      return;
    }

    if (event.type === "recipe_step") {
      setMeeting((previous) =>
        previous
          ? {
              ...previous,
              stage: "demo",
              browser_status: "connected",
              active_recipe_id: event.recipe_id ?? previous.active_recipe_id,
              current_step_index: event.step_index ?? previous.current_step_index,
              current_focus: event.page_title ?? previous.current_focus,
            }
          : previous,
      );
      if (event.narration) {
        setRuntimeNote(String(event.narration));
      }
      return;
    }

    if (event.type === "recipe_completed") {
      setRuntimeNote(`Completed walkthrough: ${event.recipe_name}`);
      return;
    }

    if (event.type === "runtime_error") {
      setLiveError(event.detail || "Live runtime error");
      setRuntimeNote(event.detail || "The live runtime hit an error.");
      return;
    }

    if (event.type === "session_ended") {
      setMeeting((previous) => (previous ? { ...previous, status: "ended" } : previous));
      setRuntimeNote("The live meeting has ended.");
    }
  }

  async function connectRoom(live: MeetingLiveStartV2) {
    const livekit = await import("livekit-client");
    const room = new livekit.Room({
      adaptiveStream: false,
      dynacast: false,
      audioCaptureDefaults: {
        autoGainControl: true,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    roomRef.current = room;

    room.on(livekit.RoomEvent.TrackSubscribed, (track: any, publication: any) => {
      const targetVideoElement =
        publication.trackName === "browser-video" ? browserStageVideoRef.current : undefined;
      const element = targetVideoElement ? track.attach(targetVideoElement) : track.attach();
      element.className = "h-full w-full";
      if (element instanceof HTMLVideoElement) {
        element.autoplay = true;
        element.playsInline = true;
        element.muted = true;
        element.style.objectFit = "contain";
        element.style.width = "1px";
        element.style.height = "1px";
        element.style.display = "block";
        element.style.opacity = "0";
        element.style.pointerEvents = "none";
        element.style.position = "absolute";
        element.style.left = "0";
        element.style.top = "0";
        void element.play().catch(() => undefined);
      } else if (element instanceof HTMLAudioElement) {
        element.autoplay = true;
      }

      if (publication.trackName === "browser-video") {
        if (typeof publication.setSubscribed === "function") {
          publication.setSubscribed(true);
        }
        if (typeof publication.setVideoQuality === "function" && livekit.VideoQuality) {
          publication.setVideoQuality(livekit.VideoQuality.HIGH);
        }
        browserVideoElementRef.current = element instanceof HTMLVideoElement ? element : null;
        browserAttachStartedAtRef.current = performance.now();

        if (element instanceof HTMLVideoElement) {
          element.onloadeddata = () => {
            console.info("[browser-stage] track loadeddata", {
              trackName: publication.trackName,
              videoWidth: element.videoWidth,
              videoHeight: element.videoHeight,
              readyState: element.readyState,
              requestedQuality:
                typeof publication.videoQuality !== "undefined" ? publication.videoQuality : "unknown",
            });
            browserTrackReadyRef.current = false;
            browserStageStateRef.current = "attaching";
            setBrowserTrackReady(false);
            setBrowserStageState("attaching");
            setRuntimeNote("Browser track attached. Rendering live frames.");
            setLiveError(null);
            startBrowserCanvasRender();
          };
          element.onplaying = async () => {
            const average = await sampleVideoBrightness(element);
            console.info("[browser-stage] track playing", {
              trackName: publication.trackName,
              videoWidth: element.videoWidth,
              videoHeight: element.videoHeight,
              readyState: element.readyState,
              averageBrightness: Number(average.toFixed(2)),
              requestedQuality:
                typeof publication.videoQuality !== "undefined" ? publication.videoQuality : "unknown",
            });
            browserTrackReadyRef.current = false;
            browserStageStateRef.current = "attaching";
            setBrowserTrackReady(false);
            setBrowserStageState("attaching");
            setRuntimeNote("Live browser video is playing.");
            setLiveError(null);
            startBrowserCanvasRender();
          };
        }
        return;
      }

      if (publication.trackName === "agent-audio") {
        if (audioContainerRef.current) {
          audioContainerRef.current.innerHTML = "";
          audioContainerRef.current.appendChild(element);
        }
        setAudioReady(true);
        setAudioUnlockNeeded(true);
        void tryStartRoomAudio();
      }
    });

    room.on(livekit.RoomEvent.TrackUnsubscribed, (track: any) => {
      if (track.kind === livekit.Track.Kind.Video && browserStageVideoRef.current) {
        track.detach(browserStageVideoRef.current);
      } else {
        track.detach().forEach((element: HTMLElement) => element.remove());
      }
      if (track.kind === livekit.Track.Kind.Video) {
        browserVideoElementRef.current = null;
        stopBrowserCanvasRender();
        browserTrackReadyRef.current = false;
        browserStageStateRef.current = "attaching";
        setBrowserTrackReady(false);
        setBrowserStageState("attaching");
        browserAttachStartedAtRef.current = null;
        if (browserStageVideoRef.current) {
          browserStageVideoRef.current.pause();
          browserStageVideoRef.current.removeAttribute("src");
          browserStageVideoRef.current.srcObject = null;
        }
        if (browserVideoReadyTimerRef.current) {
          clearTimeout(browserVideoReadyTimerRef.current);
          browserVideoReadyTimerRef.current = null;
        }
      }
      if (track.kind === livekit.Track.Kind.Audio) {
        setAudioReady(false);
        setAudioUnlockNeeded(false);
      }
    });

    await room.connect(live.livekit_url!, live.participant_token!);
    void tryStartRoomAudio();

    try {
      await room.localParticipant.setMicrophoneEnabled(true);
      setMicReady(true);
      setRuntimeNote("Microphone is live. Ask a short question and pause.");
      appendSystemMessage("Microphone is live. Ask a short question and pause.");
    } catch {
      setMicReady(false);
      appendSystemMessage("Microphone access was denied. The meeting stays available in text mode.");
    }
  }

  function connectEvents(live: MeetingLiveStartV2) {
    if (!live.event_ws_url) return;

    const socket = new WebSocket(live.event_ws_url);
    socket.onmessage = (event) => {
      try {
        handleLiveEvent(JSON.parse(event.data));
      } catch {
        // Ignore malformed runtime events.
      }
    };
    socket.onclose = () => {
      if (!closingLiveRef.current) {
        setLiveError("The live event channel closed.");
      }
    };
    wsRef.current = socket;
  }

  async function createMeetingSession() {
    updateSetup("creating", 12, "Your AI demo is getting ready", "Starting the private demo room.");
    setError(null);
    setLiveError(null);
    const created = await apiV2.createMeeting({
      public_token: token,
      language: selectedLanguage,
    });
    setMeeting(created);
    const transcript = await apiV2.getMessages(created.id);
    setMessages(transcript);
    return created;
  }

  async function prepareVoiceSession(meetingId: string) {
    updateSetup("voice", 34, "Joining the voice room", "Preparing the voice channel and meeting room.");
    const contract = await apiV2.joinMeeting(meetingId);
    setMeeting((previous) =>
      previous
        ? {
            ...previous,
            rtc_status: "ready",
            live_room_name: contract.room_name,
            live_participant_identity: contract.participant_identity,
          }
        : previous,
    );
    return contract;
  }

  async function prepareBrowserPlan(meetingId: string) {
    updateSetup("browser", 58, "Connecting the live product", "Preparing the browser agent for the product walkthrough.");
    const plan = await apiV2.planBrowser(meetingId);
    setBrowserPlan(plan);
    setMeeting((previous) => (previous ? { ...previous, browser_status: "planned" } : previous));
    return plan;
  }

  async function bootstrapMeeting(existingMeeting?: MeetingSessionV2 | null) {
    try {
      const activeMeeting = existingMeeting ?? (meeting ?? (await createMeetingSession()));
      await Promise.all([
        prepareVoiceSession(activeMeeting.id),
        prepareBrowserPlan(activeMeeting.id),
      ]);
      await startLiveMeeting(activeMeeting.id);
      updateSetup("ready", 100, "The demo room is ready", "Everything is connected. Ask naturally.");
    } catch (cause: any) {
      setSetupPhase("failed");
      setSetupProgress(100);
      setSetupHeadline("Could not start the live demo");
      setLiveError(cause.message || "Could not prepare the live demo.");
      setError(cause.message || "Could not prepare the live demo.");
    }
  }

  async function changeLanguage(language: string) {
    setSelectedLanguage(language);
    try {
      window.localStorage.setItem("demo-preferred-language", language);
    } catch {
      // Ignore local storage failures.
    }

    if (!meeting) return;
    try {
      const updated = await apiV2.updateMeetingPreferences(meeting.id, { language });
      setMeeting(updated);
      setRuntimeNote(`Language set to ${LANGUAGE_OPTIONS.find((item) => item.value === language)?.label || "English"}.`);
    } catch (cause: any) {
      setLiveError(cause.message || "Could not update language preference.");
    }
  }

  async function sendMessage(event: React.FormEvent) {
    event.preventDefault();
    if (!meeting || !input.trim() || submitting) return;

    const content = input.trim();
    setSubmitting(true);
    setInput("");

    const optimisticUser: MeetingMessageV2 = {
      id: `temp-${Date.now()}`,
      session_id: meeting.id,
      role: "user",
      content,
      message_type: "text",
      stage: meeting.stage,
      next_actions_json: "[]",
      metadata_json: null,
      created_at: new Date().toISOString(),
    };

    setMessages((previous) => [...previous, optimisticUser]);

    try {
      const turn = await apiV2.sendMessage(meeting.id, content);
      setRuntimeNote(describeTurn(turn));
      setMeeting((previous) =>
        previous
          ? {
              ...previous,
              stage: turn.stage,
              current_focus: turn.message.stage === "demo" ? content : previous.current_focus,
              active_recipe_id: turn.recipe_id ?? previous.active_recipe_id,
              browser_status: turn.stage === "demo" ? "planned" : previous.browser_status,
            }
          : previous,
      );
      setMessages((previous) => [...previous.filter((message) => message.id !== optimisticUser.id), optimisticUser, turn.message]);
    } catch (cause: any) {
      setMessages((previous) => previous.filter((message) => message.id !== optimisticUser.id));
      setError(cause.message || "Could not send the message.");
    } finally {
      setSubmitting(false);
    }
  }

  async function startLiveMeeting(meetingIdOverride?: string) {
    const targetMeetingId = meetingIdOverride ?? meeting?.id;
    if (!targetMeetingId) return;
    try {
      setError(null);
      setLiveError(null);
      updateSetup("live", 82, "Attaching the live stage", "Connecting browser video, voice, and the live runtime.");
      await disconnectLiveSession();
      closingLiveRef.current = false;

      const live = await apiV2.startLive(targetMeetingId);
      const capabilities = parseCapabilities(live.capabilities_json);
      setLiveInfo(live);
        setMeeting((previous) =>
          previous
            ? {
              ...previous,
              rtc_status: "joined",
              browser_status: "attaching",
                runtime_session_id: live.browser_session_id ?? previous.runtime_session_id,
                live_room_name: live.room_name ?? previous.live_room_name,
                live_participant_identity: live.participant_identity ?? previous.live_participant_identity,
            }
          : previous,
      );
      setBrowserStageState("attaching");
      setBrowserTrackReady(false);
      browserAttachStartedAtRef.current = performance.now();
      setRuntimeNote("The live room is connected and the browser stage is attaching.");

      if (!capabilities.mock_media && live.livekit_url && live.participant_token) {
        await connectRoom(live);
      } else {
        setBrowserTrackReady(false);
        setAudioReady(Boolean(capabilities.voice));
      }
      connectEvents(live);
    } catch (cause: any) {
      setLiveError(cause.message || "Could not start the live meeting.");
      throw cause;
    }
  }

  async function sendLiveControl(action: "pause" | "resume" | "next-step" | "restart") {
    if (!meeting) return;
    try {
      setLiveError(null);
      const response =
        action === "pause"
          ? await apiV2.pauseLive(meeting.id)
          : action === "resume"
            ? await apiV2.resumeLive(meeting.id)
            : action === "next-step"
              ? await apiV2.nextLiveStep(meeting.id)
              : await apiV2.restartLive(meeting.id);

      setMeeting((previous) =>
        previous
          ? {
              ...previous,
              rtc_status: response.live_status === "live" || response.live_status === "paused" ? "joined" : previous.rtc_status,
              active_recipe_id: response.active_recipe_id ?? previous.active_recipe_id,
              current_step_index: response.current_step_index,
            }
          : previous,
      );
      if (response.detail) {
        setRuntimeNote(response.detail);
      }
    } catch (cause: any) {
      setLiveError(cause.message || "Could not control the live meeting.");
    }
  }

  const suggestedPrompts = [
    "Show me the dashboard",
    "Show me invoices",
    "How would this fit my team?",
    "Can I get annual pricing?",
  ];

  const stageStatusLabel =
    effectiveBrowserStageState === "live"
      ? "live"
      : effectiveBrowserStageState === "black_frames"
        ? "black frames"
        : effectiveBrowserStageState === "errored"
          ? "errored"
          : "attaching";

  const stageOverlayTitle =
    effectiveBrowserStageState === "black_frames"
      ? "The browser track is attached, but frames are black."
      : effectiveBrowserStageState === "errored"
        ? "The live browser stage failed."
        : "Connecting the live browser stage.";

  const stageOverlayBody =
    effectiveBrowserStageState === "black_frames"
      ? "The browser video track is connected, but the published frames are not rendering correctly yet."
      : effectiveBrowserStageState === "errored"
        ? liveError || "The live browser stage could not be attached."
        : "Live browser frames are loading from the backend session.";

  async function retryBootstrap() {
    await disconnectLiveSession();
    bootstrapStartedRef.current = true;
    await bootstrapMeeting(meeting);
  }

  if (!meeting || isBootstrapping || setupPhase === "failed") {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(232,168,76,0.14),transparent_32%),linear-gradient(180deg,#0A0A0B_0%,#101012_100%)] px-6 py-10 text-[var(--text-primary)]">
        <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl items-center justify-center">
          <section className="w-full max-w-3xl rounded-[32px] border border-[var(--border-subtle)] bg-[rgba(20,20,22,0.88)] p-8 shadow-[0_28px_80px_rgba(0,0,0,0.34)] backdrop-blur md:p-10">
            <div className="mx-auto max-w-2xl text-center">
              <div className="inline-flex items-center gap-3 rounded-full border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-2 text-[11px] uppercase tracking-[0.24em] text-[var(--text-secondary)]">
                <span className="h-2 w-2 rounded-full bg-[var(--accent-primary)] shadow-[0_0_18px_rgba(232,168,76,0.5)]" />
                DemoAgent
              </div>

              <div className="mx-auto mt-8 max-w-xl rounded-[28px] border border-[var(--border-active)] bg-[rgba(255,255,255,0.03)] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.2)]">
                <div className="rounded-[24px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.04)] p-4">
                  <div className="flex items-center justify-between text-[12px] text-[var(--text-secondary)]">
                    <span className="rounded-full bg-[rgba(255,255,255,0.08)] px-3 py-1">AI Agent</span>
                    <span className="rounded-full bg-[rgba(232,168,76,0.12)] px-3 py-1 text-[var(--accent-primary)]">
                      {setupPhase === "failed" ? "Needs attention" : "Connecting"}
                    </span>
                  </div>
                  <div className="mt-4 flex aspect-[16/9] items-center justify-center rounded-[20px] bg-[linear-gradient(180deg,rgba(255,255,255,0.06)_0%,rgba(255,255,255,0.02)_100%)]">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.04)]">
                      <div className="h-8 w-8 animate-spin rounded-full border-2 border-[rgba(232,168,76,0.22)] border-t-[var(--accent-primary)]" />
                    </div>
                  </div>
                </div>
              </div>

              <h1 className="mt-8 font-display text-[34px] leading-tight text-[var(--text-primary)] md:text-[40px]">
                {setupHeadline}
              </h1>
              <p className="mx-auto mt-3 max-w-xl text-[15px] leading-7 text-[var(--text-secondary)]">
                {liveError || error || runtimeNote}
              </p>

              <div className="mx-auto mt-8 max-w-xl">
                <div className="h-2 overflow-hidden rounded-full bg-[rgba(255,255,255,0.08)]">
                  <div
                    className="h-full rounded-full bg-[linear-gradient(90deg,#c9f36a_0%,#e8a84c_100%)] transition-all duration-500"
                    style={{ width: `${setupProgress}%` }}
                  />
                </div>
                <p className="mt-3 text-[13px] text-[var(--text-tertiary)]">{setupProgress}%</p>
              </div>

              {setupPhase === "failed" && (
                <div className="mt-8">
                  <button type="button" onClick={retryBootstrap} className="stage-button-primary">
                    Retry live setup
                  </button>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(232,168,76,0.08),transparent_28%),linear-gradient(180deg,#0A0A0B_0%,#0D0D0F_100%)] text-[var(--text-primary)]">
      <div className="mx-auto flex h-full max-w-[1680px] flex-col px-3 py-3 sm:px-5">
        <header className="mb-3 flex shrink-0 flex-wrap items-center justify-between gap-3 rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(20,20,22,0.72)] px-4 py-3 shadow-[0_18px_50px_rgba(0,0,0,0.24)] backdrop-blur">
          <div className="flex items-center gap-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-[var(--border-active)] bg-[rgba(232,168,76,0.12)] text-[12px] font-medium text-[var(--accent-primary)]">
              DA
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--text-tertiary)]">DemoAgent</p>
              <h1 className="font-display text-[20px] text-[var(--text-primary)]">{workspaceName}</h1>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <label className="stage-pill flex items-center gap-2">
              <span>Language</span>
              <select
                className="bg-transparent text-[var(--text-secondary)] outline-none"
                value={selectedLanguage}
                onChange={(event) => void changeLanguage(event.target.value)}
              >
                {LANGUAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value} className="bg-[#121214] text-[var(--text-primary)]">
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <span className="stage-pill">Voice: {meeting.rtc_status}</span>
            <span className="stage-pill">Browser: {stageStatusLabel}</span>
            {meeting.current_step_index > 0 && <span className="stage-pill">Step: {meeting.current_step_index}</span>}
            {liveInfo && (
              <>
                <button type="button" onClick={() => sendLiveControl("pause")} className="stage-button-ghost">
                  Pause
                </button>
                <button type="button" onClick={() => sendLiveControl("resume")} className="stage-button-ghost">
                  Resume
                </button>
                <button type="button" onClick={() => sendLiveControl("next-step")} className="stage-button-ghost">
                  Next
                </button>
                <button type="button" onClick={() => sendLiveControl("restart")} className="stage-button-ghost">
                  Restart
                </button>
              </>
            )}
          </div>
        </header>

        <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
          <section className="flex min-h-0 flex-col gap-2 rounded-[28px] border border-[var(--border-subtle)] bg-[rgba(20,20,22,0.6)] p-2 shadow-[0_20px_60px_rgba(0,0,0,0.28)]">
            <div className="relative min-h-0 flex-1 overflow-hidden rounded-[30px] border border-[var(--demo-border)] bg-[rgba(255,255,255,0.02)] p-2 shadow-[var(--demo-shadow)]">
              <div className="absolute inset-x-12 top-0 h-20 rounded-full bg-[var(--accent-primary-glow)] blur-3xl" />
              <div className="relative h-full overflow-hidden rounded-[24px] border border-[var(--demo-border)] bg-[#030304]">
                <div
                  ref={browserContainerRef}
                  data-testid="browser-track-container"
                  className="absolute inset-0"
                />
                <video
                  ref={browserStageVideoRef}
                  className="pointer-events-none absolute left-0 top-0 h-px w-px opacity-0"
                  autoPlay
                  playsInline
                  muted
                  aria-hidden="true"
                />
                <canvas
                  ref={browserCanvasRef}
                  className="pointer-events-none absolute inset-0 z-[1] h-full w-full"
                />
                {effectiveBrowserStageState !== "live" && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="max-w-lg space-y-3 text-center">
                      <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-tertiary)]">Live product session</p>
                      <h2 className="font-display text-[32px] text-[var(--text-primary)]">
                        {stageOverlayTitle}
                      </h2>
                      <p className="text-[15px] leading-7 text-[var(--text-secondary)]">
                        {stageOverlayBody}
                      </p>
                    </div>
                  </div>
                )}

                <div className="absolute left-3 top-3 flex flex-wrap items-center gap-2">
                  {audioReady && <span className="stage-pill">Agent audio on</span>}
                  {micReady && <span className="stage-pill">Mic live</span>}
                </div>
              </div>
            </div>

            <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 rounded-[18px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Now showing</p>
                <p className="truncate text-[14px] text-[var(--text-secondary)]">{currentFocus || "Waiting for the first prompt."}</p>
              </div>
              <div className="min-w-0 flex-[1_1_320px] text-right text-[13px] text-[var(--text-tertiary)]">
                <p className="truncate">{stageNarrative}</p>
              </div>
            </div>
          </section>

          <aside className="flex min-h-0 flex-col overflow-hidden rounded-[26px] border border-[var(--border-subtle)] bg-[rgba(20,20,22,0.88)] shadow-[0_20px_60px_rgba(0,0,0,0.28)]">
            <div className="shrink-0 border-b border-[var(--border-subtle)] px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--text-tertiary)]">Conversation</p>
              <h2 className="mt-1 font-display text-[20px] text-[var(--text-primary)]">Ask naturally</h2>
              <p className="mt-2 text-[13px] leading-6 text-[var(--text-secondary)]">
                The agent answers here while driving the product on the left.
              </p>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4" role="log" aria-live="polite">
              <div className="space-y-3">
                {messages.map((message) => (
                  <DemoStageMessage key={message.id} message={message} />
                ))}
                <div ref={scrollRef} />
              </div>
            </div>

            <div className="shrink-0 border-t border-[var(--border-subtle)] px-4 py-4">
              {(error || liveError) && (
                <div className="mb-3 rounded-2xl border border-[rgba(255,69,58,0.35)] bg-[rgba(255,69,58,0.12)] px-4 py-3 text-[13px] leading-6 text-[#ffd2ce]">
                  {liveError || error}
                </div>
              )}

              <form onSubmit={sendMessage}>
                <div className="flex gap-3">
                  <input
                    className="stage-input flex-1"
                    placeholder="Ask anything about the product..."
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    disabled={submitting}
                  />
                  <button type="submit" className="stage-button-primary shrink-0" disabled={!input.trim() || submitting}>
                    Send
                  </button>
                </div>
              </form>

              {showSuggestedPrompts && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {suggestedPrompts.slice(0, 3).map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="stage-button-ghost"
                      onClick={() => setInput(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </aside>
        </div>
        <div ref={audioContainerRef} data-testid="audio-track-container" className="hidden" />
      </div>
    </div>
  );
}
