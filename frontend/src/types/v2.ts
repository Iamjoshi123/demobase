export interface MeetingSessionV2 {
  id: string;
  workspace_id: string;
  buyer_name: string | null;
  buyer_email: string | null;
  company_name: string | null;
  role_title: string | null;
  goal: string | null;
  status: string;
  stage: string;
  rtc_status: string;
  browser_status: string;
  current_focus: string | null;
  runtime_session_id: string | null;
  active_recipe_id: string | null;
  current_step_index: number;
  live_room_name: string | null;
  live_participant_identity: string | null;
  personalization_json: string;
  created_at: string;
  updated_at: string;
}

export interface MeetingMessageV2 {
  id: string;
  session_id: string;
  role: "user" | "agent" | "system";
  content: string;
  message_type: string;
  stage: string | null;
  next_actions_json: string;
  metadata_json: string | null;
  created_at: string;
}

export interface MeetingCreateV2 {
  public_token: string;
  buyer_name?: string;
  buyer_email?: string;
  company_name?: string;
  role_title?: string;
  goal?: string;
  language?: string;
}

export interface MeetingPreferencesUpdateV2 {
  language?: string;
}

export interface MeetingTurnV2 {
  message: MeetingMessageV2;
  stage: string;
  policy_decision: string;
  next_actions: string[];
  citations: string[];
  recipe_id: string | null;
  browser_instruction: string | null;
  action_strategy: string | null;
  should_handoff: boolean;
}

export interface MeetingJoinV2 {
  room_name: string;
  livekit_url: string;
  participant_identity: string;
  participant_name: string;
  participant_token: string;
  capabilities_json: string;
  event_ws_url?: string | null;
}

export interface MeetingBrowserPlanV2 {
  session_id: string;
  product_url: string | null;
  allowed_domains: string[];
  suggested_recipe_id: string | null;
  suggested_recipe_name: string | null;
  launch_mode: string;
  status: string;
}

export interface MeetingLiveStartV2 {
  mode: string;
  livekit_url: string | null;
  room_name: string | null;
  participant_token: string | null;
  participant_identity: string | null;
  participant_name: string | null;
  event_ws_url: string | null;
  browser_session_id: string | null;
  capabilities_json: string;
  message: string | null;
}

export interface MeetingLiveControlV2 {
  session_id: string;
  live_status: string;
  active_recipe_id: string | null;
  current_step_index: number;
  detail: string | null;
}
