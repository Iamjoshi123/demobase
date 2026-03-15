"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

export default function WorkspaceDetailPage() {
  const params = useParams<{ id: string }>();
  const wsId = params?.id ?? "";

  const [workspace, setWorkspace] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [credentials, setCredentials] = useState<any[]>([]);
  const [recipes, setRecipes] = useState<any[]>([]);
  const [policies, setPolicies] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);

  // Form states
  const [docForm, setDocForm] = useState({ filename: "", content_text: "", file_type: "md" });
  const [credForm, setCredForm] = useState({ label: "", login_url: "", username: "", password: "" });
  const [policyForm, setPolicyForm] = useState({ rule_type: "blocked_topic", pattern: "", description: "", action: "refuse", severity: "high" });
  const [recipeForm, setRecipeForm] = useState({ name: "", description: "", trigger_phrases: "", steps_json: "[]", priority: 0 });

  const loadAll = useCallback(async () => {
    try {
      const [ws, docs, creds, recs, pols, sess] = await Promise.all([
        api.getWorkspace(wsId),
        api.listDocuments(wsId),
        api.listCredentials(wsId),
        api.listRecipes(wsId),
        api.listPolicies(wsId),
        api.getWorkspaceSessions(wsId),
      ]);
      setWorkspace(ws);
      setDocuments(docs);
      setCredentials(creds);
      setRecipes(recs);
      setPolicies(pols);
      setSessions(sess);
    } catch (e) {
      console.error("Failed to load workspace data:", e);
    } finally {
      setLoading(false);
    }
  }, [wsId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  async function handleUploadDoc(e: React.FormEvent) {
    e.preventDefault();
    const formData = new FormData();
    formData.append("filename", docForm.filename);
    formData.append("file_type", docForm.file_type);
    formData.append("content_text", docForm.content_text);
    await api.uploadDocument(wsId, formData);
    setDocForm({ filename: "", content_text: "", file_type: "md" });
    const docs = await api.listDocuments(wsId);
    setDocuments(docs);
  }

  async function handleAddCred(e: React.FormEvent) {
    e.preventDefault();
    await api.addCredential(wsId, credForm);
    setCredForm({ label: "", login_url: "", username: "", password: "" });
    const creds = await api.listCredentials(wsId);
    setCredentials(creds);
  }

  async function handleAddPolicy(e: React.FormEvent) {
    e.preventDefault();
    await api.createPolicy(wsId, policyForm);
    setPolicyForm({ rule_type: "blocked_topic", pattern: "", description: "", action: "refuse", severity: "high" });
    const pols = await api.listPolicies(wsId);
    setPolicies(pols);
  }

  async function handleAddRecipe(e: React.FormEvent) {
    e.preventDefault();
    await api.createRecipe(wsId, recipeForm);
    setRecipeForm({ name: "", description: "", trigger_phrases: "", steps_json: "[]", priority: 0 });
    const recs = await api.listRecipes(wsId);
    setRecipes(recs);
  }

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>;
  if (!workspace) return <div className="p-8 text-red-500">Workspace not found</div>;

  const tabs = [
    { key: "overview", label: "Overview" },
    { key: "documents", label: `Documents (${documents.length})` },
    { key: "credentials", label: `Credentials (${credentials.length})` },
    { key: "recipes", label: `Recipes (${recipes.length})` },
    { key: "policies", label: `Policies (${policies.length})` },
    { key: "sessions", label: `Sessions (${sessions.length})` },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <Link href="/admin" className="text-sm text-gray-500 hover:text-gray-700">&larr; All Workspaces</Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{workspace.name}</h1>
          <p className="text-sm text-gray-500">{workspace.description}</p>
          <div className="mt-3 flex gap-3 text-xs">
            <span className="badge-blue">Token: {workspace.public_token}</span>
            <a
              href={`/demo/${workspace.public_token}`}
              target="_blank"
              className="badge-green hover:underline"
            >
              Demo Link &rarr;
            </a>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-6 flex gap-1 border-t border-gray-100">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? "border-primary-500 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card text-center">
              <p className="text-3xl font-bold text-primary-600">{documents.length}</p>
              <p className="text-sm text-gray-500 mt-1">Documents</p>
            </div>
            <div className="card text-center">
              <p className="text-3xl font-bold text-green-600">{credentials.length}</p>
              <p className="text-sm text-gray-500 mt-1">Credentials</p>
            </div>
            <div className="card text-center">
              <p className="text-3xl font-bold text-purple-600">{recipes.length}</p>
              <p className="text-sm text-gray-500 mt-1">Recipes</p>
            </div>
            <div className="card text-center">
              <p className="text-3xl font-bold text-orange-600">{sessions.length}</p>
              <p className="text-sm text-gray-500 mt-1">Sessions</p>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === "documents" && (
          <div className="space-y-6">
            <div className="card">
              <h3 className="font-semibold mb-4">Upload Document</h3>
              <form onSubmit={handleUploadDoc} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <input className="input" placeholder="Filename (e.g., guide.md)" value={docForm.filename}
                    onChange={(e) => setDocForm({ ...docForm, filename: e.target.value })} required />
                  <select className="input" value={docForm.file_type}
                    onChange={(e) => setDocForm({ ...docForm, file_type: e.target.value })}>
                    <option value="md">Markdown</option>
                    <option value="txt">Text</option>
                    <option value="manual_note">Manual Note</option>
                  </select>
                </div>
                <textarea className="textarea" rows={5} placeholder="Paste document content here..."
                  value={docForm.content_text}
                  onChange={(e) => setDocForm({ ...docForm, content_text: e.target.value })} required />
                <button type="submit" className="btn-primary">Upload &amp; Ingest</button>
              </form>
            </div>
            <div className="space-y-2">
              {documents.map((doc) => (
                <div key={doc.id} className="card flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium">{doc.filename}</p>
                    <p className="text-xs text-gray-400">{doc.file_type} &bull; {doc.status}</p>
                  </div>
                  <button onClick={() => { api.deleteDocument(wsId, doc.id).then(() => loadAll()); }}
                    className="text-red-500 text-sm hover:underline">Delete</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Credentials Tab */}
        {activeTab === "credentials" && (
          <div className="space-y-6">
            <div className="card">
              <h3 className="font-semibold mb-4">Add Sandbox Credential</h3>
              <form onSubmit={handleAddCred} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <input className="input" placeholder="Label (e.g., demo-user-1)" value={credForm.label}
                    onChange={(e) => setCredForm({ ...credForm, label: e.target.value })} required />
                  <input className="input" placeholder="Login URL" value={credForm.login_url}
                    onChange={(e) => setCredForm({ ...credForm, login_url: e.target.value })} required />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <input className="input" placeholder="Username / Email" value={credForm.username}
                    onChange={(e) => setCredForm({ ...credForm, username: e.target.value })} required />
                  <input className="input" type="password" placeholder="Password" value={credForm.password}
                    onChange={(e) => setCredForm({ ...credForm, password: e.target.value })} required />
                </div>
                <button type="submit" className="btn-primary">Add Credential</button>
              </form>
            </div>
            <div className="space-y-2">
              {credentials.map((cred) => (
                <div key={cred.id} className="card flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium">{cred.label}</p>
                    <p className="text-xs text-gray-400">{cred.login_url}</p>
                  </div>
                  <span className={cred.is_active ? "badge-green" : "badge-red"}>
                    {cred.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recipes Tab */}
        {activeTab === "recipes" && (
          <div className="space-y-6">
            <div className="card">
              <h3 className="font-semibold mb-4">Create Demo Recipe</h3>
              <form onSubmit={handleAddRecipe} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <input className="input" placeholder="Recipe name" value={recipeForm.name}
                    onChange={(e) => setRecipeForm({ ...recipeForm, name: e.target.value })} required />
                  <input className="input" type="number" placeholder="Priority" value={recipeForm.priority}
                    onChange={(e) => setRecipeForm({ ...recipeForm, priority: parseInt(e.target.value) || 0 })} />
                </div>
                <input className="input" placeholder="Description" value={recipeForm.description}
                  onChange={(e) => setRecipeForm({ ...recipeForm, description: e.target.value })} />
                <input className="input" placeholder="Trigger phrases (comma-separated)" value={recipeForm.trigger_phrases}
                  onChange={(e) => setRecipeForm({ ...recipeForm, trigger_phrases: e.target.value })} />
                <textarea className="textarea font-mono text-sm" rows={6} placeholder='Steps JSON: [{"action":"navigate","target":"http://..."}]'
                  value={recipeForm.steps_json}
                  onChange={(e) => setRecipeForm({ ...recipeForm, steps_json: e.target.value })} required />
                <button type="submit" className="btn-primary">Create Recipe</button>
              </form>
            </div>
            <div className="space-y-2">
              {recipes.map((r) => (
                <div key={r.id} className="card py-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{r.name}</p>
                      <p className="text-xs text-gray-400">{r.description}</p>
                      <p className="text-xs text-gray-400 mt-1">Triggers: {r.trigger_phrases}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="badge-blue">Priority: {r.priority}</span>
                      <button onClick={() => { api.deleteRecipe(wsId, r.id).then(() => loadAll()); }}
                        className="text-red-500 text-sm hover:underline">Delete</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Policies Tab */}
        {activeTab === "policies" && (
          <div className="space-y-6">
            <div className="card">
              <h3 className="font-semibold mb-4">Add Policy Rule</h3>
              <form onSubmit={handleAddPolicy} className="space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  <select className="input" value={policyForm.rule_type}
                    onChange={(e) => setPolicyForm({ ...policyForm, rule_type: e.target.value })}>
                    <option value="blocked_topic">Blocked Topic</option>
                    <option value="blocked_action">Blocked Action</option>
                    <option value="escalation_condition">Escalation Condition</option>
                    <option value="allowed_route">Allowed Route</option>
                    <option value="blocked_route">Blocked Route</option>
                  </select>
                  <select className="input" value={policyForm.action}
                    onChange={(e) => setPolicyForm({ ...policyForm, action: e.target.value })}>
                    <option value="refuse">Refuse</option>
                    <option value="escalate">Escalate</option>
                    <option value="warn">Warn</option>
                  </select>
                  <select className="input" value={policyForm.severity}
                    onChange={(e) => setPolicyForm({ ...policyForm, severity: e.target.value })}>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <input className="input" placeholder="Pattern (regex)" value={policyForm.pattern}
                  onChange={(e) => setPolicyForm({ ...policyForm, pattern: e.target.value })} required />
                <input className="input" placeholder="Description" value={policyForm.description}
                  onChange={(e) => setPolicyForm({ ...policyForm, description: e.target.value })} />
                <button type="submit" className="btn-primary">Add Policy</button>
              </form>
            </div>
            <div className="space-y-2">
              {policies.map((p) => (
                <div key={p.id} className="card flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium">{p.description || p.pattern}</p>
                    <p className="text-xs text-gray-400">
                      {p.rule_type} &bull; Action: {p.action} &bull; Pattern: <code className="bg-gray-100 px-1 rounded">{p.pattern}</code>
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <span className={p.severity === "high" ? "badge-red" : p.severity === "medium" ? "badge-yellow" : "badge-blue"}>
                      {p.severity}
                    </span>
                    <button onClick={() => { api.deletePolicy(wsId, p.id).then(() => loadAll()); }}
                      className="text-red-500 text-sm hover:underline">Delete</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sessions Tab */}
        {activeTab === "sessions" && (
          <div className="space-y-2">
            {sessions.length === 0 ? (
              <p className="text-gray-500">No sessions yet. Share the demo link to start getting sessions.</p>
            ) : (
              sessions.map((s: any) => (
                <Link key={s.id} href={`/admin/workspaces/${wsId}/sessions?session=${s.id}`}
                  className="card flex items-center justify-between py-3 hover:shadow-md transition-shadow block">
                  <div>
                    <p className="font-medium">{s.buyer_name || "Anonymous"}</p>
                    <p className="text-xs text-gray-400">
                      {s.mode} &bull; {new Date(s.started_at).toLocaleString()}
                      {s.ended_at && ` - ${new Date(s.ended_at).toLocaleString()}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {s.lead_intent_score != null && (
                      <span className={`badge ${s.lead_intent_score >= 70 ? "badge-green" : s.lead_intent_score >= 40 ? "badge-yellow" : "badge-red"}`}>
                        Score: {s.lead_intent_score}
                      </span>
                    )}
                    <span className={s.status === "active" ? "badge-green" : "badge-blue"}>
                      {s.status}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  );
}
