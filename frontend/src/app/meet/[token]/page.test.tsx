import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MeetingPageV2 from "./page";

const apiMock = vi.hoisted(() => ({
  createMeeting: vi.fn(),
  getMessages: vi.fn(),
  sendMessage: vi.fn(),
  joinMeeting: vi.fn(),
  startLive: vi.fn(),
  greetLive: vi.fn(),
  pauseLive: vi.fn(),
  resumeLive: vi.fn(),
  nextLiveStep: vi.fn(),
  restartLive: vi.fn(),
  planBrowser: vi.fn(),
  updateMeetingPreferences: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: "demo-token-v2" }),
}));

vi.mock("@/lib/api-v2", () => ({
  apiV2: apiMock,
}));

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

describe("MeetingPageV2", () => {
  function deferred<T>() {
    let resolve!: (value: T | PromiseLike<T>) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
      resolve = res;
      reject = rej;
    });
    return { promise, resolve, reject };
  }

  function mockBootstrap({
    buyerName = "Riley",
    companyName = "Northwind",
    goal = "Understand reporting workflows",
  }: {
    buyerName?: string | null;
    companyName?: string | null;
    goal?: string | null;
  } = {}) {
    apiMock.createMeeting.mockResolvedValue({
      id: "meeting-1",
      workspace_id: "ws-1",
      buyer_name: buyerName,
      buyer_email: null,
      company_name: companyName,
      role_title: "Sales Ops Lead",
      goal,
      status: "active",
      stage: "intro",
      rtc_status: "not_started",
      browser_status: "not_started",
      current_focus: null,
      runtime_session_id: null,
      active_recipe_id: null,
      current_step_index: 0,
      live_room_name: null,
      live_participant_identity: null,
      personalization_json: "{}",
      created_at: "2026-03-12T00:00:00.000Z",
      updated_at: "2026-03-12T00:00:00.000Z",
    });
    apiMock.getMessages.mockResolvedValue([
      {
        id: "msg-1",
        session_id: "meeting-1",
        role: "agent",
        content: "Welcome Riley. I'll tailor this Acme CRM walkthrough.",
        message_type: "text",
        stage: "intro",
        next_actions_json: '["clarify_buyer_goal"]',
        metadata_json: '{"workspace_name":"Acme CRM"}',
        created_at: "2026-03-12T00:00:00.000Z",
      },
    ]);
    apiMock.joinMeeting.mockResolvedValue({
      room_name: "meeting-meeting-1",
      livekit_url: "ws://localhost:7880",
      participant_identity: "buyer-meeting-1",
      participant_name: buyerName || "Riley",
      participant_token: "token",
      capabilities_json: '{"voice":true}',
      event_ws_url: null,
    });
    apiMock.planBrowser.mockResolvedValue({
      session_id: "meeting-1",
      product_url: "https://app.example.com",
      allowed_domains: ["app.example.com"],
      suggested_recipe_id: "recipe-1",
      suggested_recipe_name: "Dashboard Tour",
      launch_mode: "browser_worker",
      status: "planned",
    });
    apiMock.startLive.mockResolvedValue({
      mode: "live",
      livekit_url: "ws://localhost:7880",
      room_name: "meeting-meeting-1",
      participant_token: "token",
      participant_identity: "buyer-meeting-1",
      participant_name: buyerName || "Riley",
      event_ws_url: null,
      browser_session_id: "runtime-1",
      capabilities_json: '{"voice":true,"video":true,"mock_media":true,"assist_controls":["pause","resume","next-step","restart"]}',
      message: "Live meeting ready",
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket as any);
    mockBootstrap();
  });

  it("auto-starts the meeting and loads the welcome transcript", async () => {
    const pendingMeeting = deferred<any>();
    apiMock.createMeeting.mockReturnValueOnce(pendingMeeting.promise);

    render(<MeetingPageV2 />);

    expect(await screen.findByText("Your AI demo is getting ready")).toBeInTheDocument();

    expect(apiMock.createMeeting).toHaveBeenCalledWith({
      public_token: "demo-token-v2",
      language: "en",
    });

    pendingMeeting.resolve({
      id: "meeting-1",
      workspace_id: "ws-1",
      buyer_name: "Riley",
      buyer_email: null,
      company_name: "Northwind",
      role_title: "Sales Ops Lead",
      goal: "Understand reporting workflows",
      status: "active",
      stage: "intro",
      rtc_status: "not_started",
      browser_status: "not_started",
      current_focus: null,
      runtime_session_id: null,
      active_recipe_id: null,
      current_step_index: 0,
      live_room_name: null,
      live_participant_identity: null,
      personalization_json: "{}",
      created_at: "2026-03-12T00:00:00.000Z",
      updated_at: "2026-03-12T00:00:00.000Z",
    });

    expect(await screen.findByText("Ask naturally")).toBeInTheDocument();
    expect(screen.getByText(/Welcome Riley/)).toBeInTheDocument();
  });

  it("auto-prepares voice and browser runtime plans", async () => {
    render(<MeetingPageV2 />);

    await waitFor(() => {
      expect(apiMock.joinMeeting).toHaveBeenCalledWith("meeting-1");
      expect(apiMock.planBrowser).toHaveBeenCalledWith("meeting-1");
      expect(apiMock.startLive).toHaveBeenCalledWith("meeting-1");
    });

    expect(await screen.findByText("Voice: joined")).toBeInTheDocument();
    expect(screen.getByText("Everything is connected. Ask naturally.")).toBeInTheDocument();
  });

  it("starts the live runtime automatically and exposes assist controls", async () => {
    apiMock.pauseLive.mockResolvedValueOnce({
      session_id: "runtime-1",
      live_status: "paused",
      active_recipe_id: null,
      current_step_index: 0,
      detail: "Live demo paused",
    });

    render(<MeetingPageV2 />);
    const user = userEvent.setup();

    expect(await screen.findByText("Everything is connected. Ask naturally.")).toBeInTheDocument();
    expect(screen.getByText("Agent audio on")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Pause" }));

    expect(apiMock.pauseLive).toHaveBeenCalledWith("meeting-1");
    expect(await screen.findByText("Live demo paused")).toBeInTheDocument();
  });

  it("renders a hidden decode video and a visible browser canvas for the stage", async () => {
    const { container } = render(<MeetingPageV2 />);

    expect(await screen.findByText("Everything is connected. Ask naturally.")).toBeInTheDocument();

    const browserVideo = container.querySelector("video[aria-hidden='true']") as HTMLVideoElement | null;
    const browserCanvas = container.querySelector("canvas") as HTMLCanvasElement | null;

    expect(browserVideo).not.toBeNull();
    expect(browserCanvas).not.toBeNull();
    expect(browserVideo?.className).toContain("opacity-0");
    expect(browserCanvas?.className).not.toContain("opacity-0");
  });

  it("renders a moving pointer and click highlight without text annotations", async () => {
    apiMock.startLive.mockResolvedValueOnce({
      mode: "live",
      livekit_url: "ws://localhost:7880",
      room_name: "meeting-meeting-1",
      participant_token: "token",
      participant_identity: "buyer-meeting-1",
      participant_name: "Riley",
      event_ws_url: "ws://localhost:8000/api/v2/meetings/meeting-1/events",
      browser_session_id: "runtime-1",
      capabilities_json: '{"voice":true,"video":true,"mock_media":true,"assist_controls":["pause","resume","next-step","restart"]}',
      message: "Live meeting ready",
    });

    render(<MeetingPageV2 />);

    expect(await screen.findByText("Everything is connected. Ask naturally.")).toBeInTheDocument();
    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => {
      MockWebSocket.instances[0].onmessage?.({
        data: JSON.stringify({
          type: "browser_pointer_move",
          x: 320,
          y: 180,
          width: 1280,
          height: 720,
        }),
      });
    });

    const pointer = screen.getByTestId("browser-pointer");
    expect(pointer).toHaveStyle({ left: "25%", top: "25%", opacity: "1" });

    act(() => {
      MockWebSocket.instances[0].onmessage?.({
        data: JSON.stringify({
          type: "browser_click",
          x: 640,
          y: 360,
          width: 1280,
          height: 720,
          label: "Sequences",
        }),
      });
    });

    expect(screen.getByTestId("browser-pointer")).toHaveStyle({ left: "50%", top: "50%", opacity: "1" });
    expect(screen.getByTestId("browser-click-highlight")).toBeInTheDocument();
    expect(screen.queryByText("Sequences")).not.toBeInTheDocument();
  });

  it("sends a question and renders the agent next actions", async () => {
    apiMock.sendMessage.mockResolvedValueOnce({
      stage: "demo",
      policy_decision: "allow",
      next_actions: ["run_browser_instruction:Show the reporting dashboard", "fallback_recipe:recipe-1"],
      citations: ["doc-1"],
      recipe_id: "recipe-1",
      browser_instruction: "Show the reporting dashboard",
      action_strategy: "stagehand_then_recipe",
      should_handoff: false,
      message: {
        id: "msg-2",
        session_id: "meeting-1",
        role: "agent",
        content: "I'd show the reporting workflow next.",
        message_type: "text",
        stage: "demo",
        next_actions_json: '["run_browser_instruction:Show the reporting dashboard","fallback_recipe:recipe-1"]',
        metadata_json: '{"recipe_name":"Reporting","action_strategy":"stagehand_then_recipe"}',
        created_at: "2026-03-12T00:01:00.000Z",
      },
    });

    render(<MeetingPageV2 />);
    const user = userEvent.setup();

    await user.type(await screen.findByPlaceholderText("Ask anything about the product..."), "Show me the dashboard");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(apiMock.sendMessage).toHaveBeenCalledWith("meeting-1", "Show me the dashboard");
    expect(await screen.findByText("I'd show the reporting workflow next.")).toBeInTheDocument();
    expect(screen.getAllByText("Live browser action").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Structured fallback").length).toBeGreaterThan(0);
  });
});
