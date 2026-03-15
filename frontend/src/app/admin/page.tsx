"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Workspace } from "@/types/api";

export default function AdminPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    product_url: "",
    allowed_domains: "",
    browser_auth_mode: "credentials",
  });

  useEffect(() => {
    loadWorkspaces();
  }, []);

  async function loadWorkspaces() {
    try {
      const data = await api.listWorkspaces();
      setWorkspaces(data);
    } catch (e) {
      console.error("Failed to load workspaces:", e);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.createWorkspace(form);
      setForm({
        name: "",
        description: "",
        product_url: "",
        allowed_domains: "",
        browser_auth_mode: "credentials",
      });
      setShowCreate(false);
      loadWorkspaces();
    } catch (e) {
      console.error("Failed to create workspace:", e);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">
              &larr; Home
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
          </div>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            + New Workspace
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {showCreate && (
          <div className="card mb-8">
            <h2 className="text-lg font-semibold mb-4">Create Workspace</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  className="input"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g., Acme CRM Pro"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  className="textarea"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Brief product description..."
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Product URL</label>
                  <input
                    className="input"
                    value={form.product_url}
                    onChange={(e) => setForm({ ...form, product_url: e.target.value })}
                    placeholder="https://app.example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Allowed Domains</label>
                  <input
                    className="input"
                    value={form.allowed_domains}
                    onChange={(e) => setForm({ ...form, allowed_domains: e.target.value })}
                    placeholder="example.com, app.example.com"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Browser Auth Mode</label>
                <select
                  className="input"
                  value={form.browser_auth_mode}
                  onChange={(e) => setForm({ ...form, browser_auth_mode: e.target.value })}
                >
                  <option value="credentials">Sandbox credentials</option>
                  <option value="none">No login required</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn-primary">Create</button>
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <p className="text-gray-500">Loading workspaces...</p>
        ) : workspaces.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-gray-500 mb-4">No workspaces yet. Create your first one to get started.</p>
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              + New Workspace
            </button>
          </div>
        ) : (
          <div className="grid gap-4">
            {workspaces.map((ws) => (
              <Link key={ws.id} href={`/admin/workspaces/${ws.id}`} className="card hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{ws.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">{ws.description || "No description"}</p>
                    <div className="flex gap-3 mt-2 text-xs text-gray-400">
                      <span>Token: {ws.public_token}</span>
                      <span>Auth: {ws.browser_auth_mode === "none" ? "No login" : "Credentials"}</span>
                      <span>Created: {new Date(ws.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="text-gray-400">&rarr;</div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
