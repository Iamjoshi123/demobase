/** API client for the Agentic Demo Brain backend. */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}/api${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// Workspaces
export const api = {
  // Workspaces
  listWorkspaces: () => request<any[]>("/workspaces"),
  getWorkspace: (id: string) => request<any>(`/workspaces/${id}`),
  createWorkspace: (data: any) =>
    request<any>("/workspaces", { method: "POST", body: JSON.stringify(data) }),
  updateWorkspace: (id: string, data: any) =>
    request<any>(`/workspaces/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  // Documents
  listDocuments: (wsId: string) => request<any[]>(`/workspaces/${wsId}/documents`),
  uploadDocument: async (wsId: string, formData: FormData) => {
    const url = `${API_BASE}/api/workspaces/${wsId}/documents`;
    const res = await fetch(url, { method: "POST", body: formData });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  },
  deleteDocument: (wsId: string, docId: string) =>
    request<any>(`/workspaces/${wsId}/documents/${docId}`, { method: "DELETE" }),

  // Credentials
  listCredentials: (wsId: string) => request<any[]>(`/workspaces/${wsId}/credentials`),
  addCredential: (wsId: string, data: any) =>
    request<any>(`/workspaces/${wsId}/credentials`, { method: "POST", body: JSON.stringify(data) }),
  deleteCredential: (wsId: string, credId: string) =>
    request<any>(`/workspaces/${wsId}/credentials/${credId}`, { method: "DELETE" }),

  // Recipes
  listRecipes: (wsId: string) => request<any[]>(`/workspaces/${wsId}/recipes`),
  createRecipe: (wsId: string, data: any) =>
    request<any>(`/workspaces/${wsId}/recipes`, { method: "POST", body: JSON.stringify(data) }),
  updateRecipe: (wsId: string, recipeId: string, data: any) =>
    request<any>(`/workspaces/${wsId}/recipes/${recipeId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteRecipe: (wsId: string, recipeId: string) =>
    request<any>(`/workspaces/${wsId}/recipes/${recipeId}`, { method: "DELETE" }),

  // Policies
  listPolicies: (wsId: string) => request<any[]>(`/workspaces/${wsId}/policies`),
  createPolicy: (wsId: string, data: any) =>
    request<any>(`/workspaces/${wsId}/policies`, { method: "POST", body: JSON.stringify(data) }),
  deletePolicy: (wsId: string, policyId: string) =>
    request<any>(`/workspaces/${wsId}/policies/${policyId}`, { method: "DELETE" }),

  // Sessions
  createSession: (data: any) =>
    request<any>("/sessions", { method: "POST", body: JSON.stringify(data) }),
  getSession: (sessionId: string) => request<any>(`/sessions/${sessionId}`),
  getMessages: (sessionId: string) => request<any[]>(`/sessions/${sessionId}/messages`),
  sendMessage: (sessionId: string, content: string) =>
    request<any>(`/sessions/${sessionId}/message`, {
      method: "POST",
      body: JSON.stringify({ content, message_type: "text" }),
    }),
  startBrowser: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/start-browser`, { method: "POST" }),
  startLive: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/live/start`, { method: "POST" }),
  pauseLive: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/controls/pause`, { method: "POST" }),
  resumeLive: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/controls/resume`, { method: "POST" }),
  nextLiveStep: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/controls/next-step`, { method: "POST" }),
  restartLive: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/controls/restart`, { method: "POST" }),
  executeRecipe: (sessionId: string, recipeId: string) =>
    request<any>(`/sessions/${sessionId}/execute-recipe?recipe_id=${recipeId}`, { method: "POST" }),
  getScreenshot: (sessionId: string) => request<any>(`/sessions/${sessionId}/screenshot`),
  getBrowserState: (sessionId: string) => request<any>(`/sessions/${sessionId}/browser-state`),
  endSession: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/end`, { method: "POST" }),
  getSessionSummary: (sessionId: string) => request<any>(`/sessions/${sessionId}/summary`),
  getSessionActions: (sessionId: string) => request<any[]>(`/sessions/${sessionId}/actions`),

  // Analytics
  getWorkspaceAnalytics: (wsId: string) => request<any>(`/workspaces/${wsId}/analytics`),
  getWorkspaceSessions: (wsId: string) => request<any[]>(`/workspaces/${wsId}/sessions`),

  // Voice
  startVoice: (sessionId: string) =>
    request<any>(`/sessions/${sessionId}/voice/start`, { method: "POST" }),
};
