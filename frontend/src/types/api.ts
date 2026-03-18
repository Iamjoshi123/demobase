/** Shared TypeScript interfaces matching the backend Pydantic models. */

export interface Workspace {
  id: string;
  name: string;
  description: string | null;
  product_url: string | null;
  allowed_domains: string;
  browser_auth_mode: string;
  public_token: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceCreate {
  name: string;
  description?: string;
  product_url?: string;
  allowed_domains?: string;
  browser_auth_mode?: string;
}

export interface Document {
  id: string;
  workspace_id: string;
  filename: string;
  file_type: string;
  content_text: string | null;
  status: string;
  created_at: string;
}

export interface Credential {
  id: string;
  workspace_id: string;
  label: string;
  login_url: string;
  is_active: boolean;
  created_at: string;
}

export interface CredentialCreate {
  label: string;
  login_url: string;
  username: string;
  password: string;
}

export interface DemoRecipe {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  trigger_phrases: string;
  steps_json: string;
  is_active: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface RecipeCreate {
  name: string;
  description?: string;
  trigger_phrases?: string;
  steps_json: string;
  priority: number;
}

export interface PolicyRule {
  id: string;
  workspace_id: string;
  rule_type: string;
  pattern: string;
  description: string | null;
  action: string;
  severity: string;
  is_active: boolean;
  created_at: string;
}

export interface PolicyCreate {
  rule_type: string;
  pattern: string;
  description?: string;
  action: string;
  severity: string;
}

export interface DemoSession {
  id: string;
  workspace_id: string;
  status: string;
  buyer_name: string | null;
  buyer_email: string | null;
  mode: string;
  live_status: string;
  active_recipe_id: string | null;
  current_step_index: number;
  live_room_name: string | null;
  started_at: string;
  ended_at: string | null;
}

export interface LiveStartResponse {
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

export interface LiveControlResponse {
  session_id: string;
  live_status: string;
  active_recipe_id: string | null;
  current_step_index: number;
  detail: string | null;
}

export interface SessionMessage {
  id: string;
  session_id: string;
  role: "user" | "agent" | "system";
  content: string;
  message_type: string;
  planner_decision: string | null;
  created_at: string;
}

export interface SessionSummary {
  id: string;
  session_id: string;
  summary_text: string;
  top_questions: string;
  features_interest: string;
  objections: string;
  unresolved_items: string;
  escalation_reasons: string;
  lead_intent_score: number;
  total_messages: number;
  total_actions: number;
  duration_seconds: number;
  created_at: string;
}

export interface BrowserAction {
  id: string;
  session_id: string;
  action_type: string;
  target: string | null;
  value: string | null;
  status: string;
  screenshot_path: string | null;
  error_message: string | null;
  narration: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface WorkspaceAnalytics {
  workspace_id: string;
  total_sessions: number;
  completed_sessions: number;
  average_lead_score: number;
  total_messages: number;
  total_browser_actions: number;
  top_questions: string[];
  features_interest: string[];
  objections: string[];
  sessions: {
    id: string;
    buyer_name: string | null;
    status: string;
    mode: string;
    started_at: string | null;
    ended_at: string | null;
  }[];
}

export type AgentStatus =
  | "idle"
  | "thinking"
  | "checking_docs"
  | "navigating"
  | "showing_feature"
  | "escalated"
  | "error";
