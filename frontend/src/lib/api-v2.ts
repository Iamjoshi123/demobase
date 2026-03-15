import type {
  MeetingBrowserPlanV2,
  MeetingCreateV2,
  MeetingJoinV2,
  MeetingLiveControlV2,
  MeetingLiveStartV2,
  MeetingMessageV2,
  MeetingPreferencesUpdateV2,
  MeetingSessionV2,
  MeetingTurnV2,
} from "@/types/v2";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}/api${path}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export const apiV2 = {
  createMeeting: (data: MeetingCreateV2) =>
    request<MeetingSessionV2>("/v2/meetings", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getMeeting: (meetingId: string) => request<MeetingSessionV2>(`/v2/meetings/${meetingId}`),
  updateMeetingPreferences: (meetingId: string, data: MeetingPreferencesUpdateV2) =>
    request<MeetingSessionV2>(`/v2/meetings/${meetingId}/preferences`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getMessages: (meetingId: string) => request<MeetingMessageV2[]>(`/v2/meetings/${meetingId}/messages`),
  sendMessage: (meetingId: string, content: string) =>
    request<MeetingTurnV2>(`/v2/meetings/${meetingId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, message_type: "text" }),
    }),
  joinMeeting: (meetingId: string) =>
    request<MeetingJoinV2>(`/v2/meetings/${meetingId}/join`, {
      method: "POST",
    }),
  startLive: (meetingId: string) =>
    request<MeetingLiveStartV2>(`/v2/meetings/${meetingId}/live/start`, {
      method: "POST",
    }),
  greetLive: (meetingId: string) =>
    request<{ detail: string }>(`/v2/meetings/${meetingId}/live/greet`, {
      method: "POST",
    }),
  pauseLive: (meetingId: string) =>
    request<MeetingLiveControlV2>(`/v2/meetings/${meetingId}/controls/pause`, {
      method: "POST",
    }),
  resumeLive: (meetingId: string) =>
    request<MeetingLiveControlV2>(`/v2/meetings/${meetingId}/controls/resume`, {
      method: "POST",
    }),
  nextLiveStep: (meetingId: string) =>
    request<MeetingLiveControlV2>(`/v2/meetings/${meetingId}/controls/next-step`, {
      method: "POST",
    }),
  restartLive: (meetingId: string) =>
    request<MeetingLiveControlV2>(`/v2/meetings/${meetingId}/controls/restart`, {
      method: "POST",
    }),
  planBrowser: (meetingId: string) =>
    request<MeetingBrowserPlanV2>(`/v2/meetings/${meetingId}/browser-plan`, {
      method: "POST",
    }),
  getRuntimeScreenshot: async (runtimeSessionId: string) => {
    const response = await fetch(`${API_BASE}/api/sessions/${runtimeSessionId}/screenshot?t=${Date.now()}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Screenshot unavailable: ${response.status}`);
    }
    return response.json() as Promise<{ screenshot: string }>;
  },
  getRuntimeScreenshotImageUrl: (runtimeSessionId: string, tick: number) =>
    `${API_BASE}/api/sessions/${runtimeSessionId}/screenshot.jpg?t=${tick}`,
};
