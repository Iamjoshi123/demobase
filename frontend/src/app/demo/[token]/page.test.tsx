import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DemoPage from "./page";

const apiMock = vi.hoisted(() => ({
  createSession: vi.fn(),
  getMessages: vi.fn(),
  sendMessage: vi.fn(),
  startLive: vi.fn(),
  pauseLive: vi.fn(),
  resumeLive: vi.fn(),
  nextLiveStep: vi.fn(),
  restartLive: vi.fn(),
  endSession: vi.fn(),
}));

const roomDisconnectMock = vi.fn();
const micEnableMock = vi.fn();

class MockRoom {
  handlers: Record<string, (...args: any[]) => void> = {};
  localParticipant = {
    setMicrophoneEnabled: micEnableMock,
  };

  on(event: string, handler: (...args: any[]) => void) {
    this.handlers[event] = handler;
  }

  async connect() {
    const videoTrack = {
      attach: () => {
        const element = document.createElement("video");
        element.dataset.testid = "browser-track";
        return element;
      },
      detach: () => [],
    };
    const audioTrack = {
      attach: () => {
        const element = document.createElement("audio");
        return element;
      },
      detach: () => [],
    };

    this.handlers.trackSubscribed?.(videoTrack, { trackName: "browser-video" }, {});
    this.handlers.trackSubscribed?.(audioTrack, { trackName: "agent-audio" }, {});
  }

  async disconnect() {
    roomDisconnectMock();
  }
}

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.onclose?.();
  }
}

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: "public-demo-token" }),
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("livekit-client", () => ({
  Room: MockRoom,
  RoomEvent: {
    TrackSubscribed: "trackSubscribed",
    TrackUnsubscribed: "trackUnsubscribed",
  },
}));

describe("DemoPage", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    micEnableMock.mockResolvedValue(undefined);
    roomDisconnectMock.mockResolvedValue(undefined);
    vi.stubGlobal("WebSocket", MockWebSocket as any);
  });

  it("starts a session from the public token and loads the transcript", async () => {
    apiMock.createSession.mockResolvedValueOnce({
      id: "sess-1",
      status: "active",
      live_status: "idle",
      current_step_index: 0,
      active_recipe_id: null,
      live_room_name: null,
    });
    apiMock.getMessages.mockResolvedValueOnce([
      { id: "msg-1", role: "agent", content: "Welcome", message_type: "text", created_at: "2026-03-08T00:00:00.000Z" },
    ]);

    render(<DemoPage />);
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText("Your name (optional)"), "Taylor");
    await user.click(screen.getAllByRole("button", { name: "Start Demo" })[0]);

    await waitFor(() => {
      expect(apiMock.createSession).toHaveBeenCalledWith({
        public_token: "public-demo-token",
        buyer_name: "Taylor",
        buyer_email: undefined,
        mode: "text",
      });
    });
    expect(await screen.findByText("Welcome")).toBeInTheDocument();
  });

  it("transitions to escalated state and then returns to idle", async () => {
    apiMock.createSession.mockResolvedValueOnce({
      id: "sess-1",
      status: "active",
      live_status: "idle",
      current_step_index: 0,
      active_recipe_id: null,
      live_room_name: null,
    });
    apiMock.getMessages.mockResolvedValueOnce([]);
    apiMock.sendMessage.mockResolvedValueOnce({
      id: "agent-1",
      role: "agent",
      content: "Please talk to sales.",
      message_type: "text",
      planner_decision: "escalate",
      created_at: "2026-03-08T00:00:00.000Z",
    });

    render(<DemoPage />);
    const user = userEvent.setup();

    await user.click(screen.getAllByRole("button", { name: "Start Demo" })[0]);
    await user.type(await screen.findByPlaceholderText("Ask about the product..."), "Can I get pricing?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Connecting to sales team...")).toBeInTheDocument();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 3100));
    });

    await waitFor(() => {
      expect(screen.queryByText("Connecting to sales team...")).not.toBeInTheDocument();
    });
  });

  it("shows an error when the demo link cannot start a session", async () => {
    apiMock.createSession.mockRejectedValueOnce(new Error("Invalid demo link"));

    render(<DemoPage />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Start Demo" }));

    expect(await screen.findByText("Invalid demo link")).toBeInTheDocument();
  });

  it("starts the live demo, joins the room, and handles assist controls", async () => {
    apiMock.createSession.mockResolvedValueOnce({
      id: "sess-1",
      status: "active",
      live_status: "idle",
      current_step_index: 0,
      active_recipe_id: null,
      live_room_name: null,
    });
    apiMock.getMessages.mockResolvedValueOnce([]);
    apiMock.startLive.mockResolvedValueOnce({
      mode: "live",
      livekit_url: "ws://localhost:7880",
      room_name: "demo-sess-1",
      participant_token: "buyer-token",
      participant_identity: "buyer-sess-1",
      participant_name: "Demo Buyer",
      event_ws_url: "ws://localhost:8000/api/sessions/sess-1/events",
      browser_session_id: "sess-1",
      capabilities_json: "{\"voice\":true,\"video\":true}",
      message: "Live demo ready",
    });
    apiMock.pauseLive.mockResolvedValueOnce({
      session_id: "sess-1",
      live_status: "paused",
      active_recipe_id: "recipe-1",
      current_step_index: 1,
      detail: "Live demo paused",
    });

    render(<DemoPage />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Start Demo" }));
    await user.click(await screen.findByRole("button", { name: "Start Live Demo" }));

    await waitFor(() => {
      expect(apiMock.startLive).toHaveBeenCalledWith("sess-1");
    });
    expect(await screen.findByText("Video connected")).toBeInTheDocument();
    expect(screen.getByText("Agent audio live")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Pause" }));

    expect(apiMock.pauseLive).toHaveBeenCalledWith("sess-1");
    expect((await screen.findAllByText("Live demo paused")).length).toBeGreaterThan(0);

    act(() => {
      MockWebSocket.instances[0].onmessage?.({
        data: JSON.stringify({
          type: "recipe_step",
          timestamp: "2026-03-08T00:00:01.000Z",
          step_index: 2,
          recipe_name: "Reports Tour",
          success: true,
          narration: "Opened the analytics page",
        }),
      });
    });

    expect(await screen.findByText("Opened the analytics page")).toBeInTheDocument();
  });

  it("supports a text-only answer flow and shows summary after ending the session", async () => {
    apiMock.createSession.mockResolvedValueOnce({
      id: "sess-1",
      status: "active",
      live_status: "idle",
      current_step_index: 0,
      active_recipe_id: null,
      live_room_name: null,
    });
    apiMock.getMessages.mockResolvedValueOnce([]);
    apiMock.sendMessage.mockResolvedValueOnce({
      id: "agent-1",
      role: "agent",
      content: "The dashboard includes reporting widgets.",
      message_type: "text",
      planner_decision: "answer_only",
      created_at: "2026-03-08T00:00:00.000Z",
    });
    apiMock.endSession.mockResolvedValueOnce({
      status: "ended",
      summary: { lead_intent_score: 68, summary_text: "Buyer focused on analytics." },
    });

    render(<DemoPage />);
    const user = userEvent.setup();

    await user.click(screen.getAllByRole("button", { name: "Start Demo" })[0]);
    await user.type(await screen.findByPlaceholderText("Ask about the product..."), "What dashboard widgets exist?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("The dashboard includes reporting widgets.")).toBeInTheDocument();
    expect(screen.getByText("From docs or live product")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "End Session" }));

    expect(await screen.findByText("Session ended. Lead intent score: 68")).toBeInTheDocument();
    expect(screen.getByText("Buyer focused on analytics.")).toBeInTheDocument();
  });
});
