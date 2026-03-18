"use client";

import { AdminShell } from "@/components/admin-shell";

export default function AdminSettingsPage() {
  return (
    <AdminShell
      title="Settings"
      description="Minimal environment notes for the legacy demo stack."
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="admin-panel rounded-[24px] px-5 py-5">
          <p className="admin-eyebrow">Environment</p>
          <h2 className="mt-2 text-[1.45rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Runtime</h2>
          <div className="mt-5 space-y-3 text-sm text-[var(--text-secondary)]">
            <p><span className="text-[var(--text-primary)]">API base:</span> `NEXT_PUBLIC_API_URL`</p>
            <p><span className="text-[var(--text-primary)]">Admin mode:</span> Legacy workspace compatibility</p>
            <p><span className="text-[var(--text-primary)]">Share links:</span> Derived from each product's public token</p>
          </div>
        </div>

        <div className="admin-panel rounded-[24px] px-5 py-5">
          <p className="admin-eyebrow">Scope</p>
          <h2 className="mt-2 text-[1.45rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">What this stack supports</h2>
          <p className="mt-5 text-sm leading-7 text-[var(--text-secondary)]">
            `demobase` keeps the older control plane. Products map to workspaces, knowledge maps to documents, and agent behavior maps to credentials, recipes, and policies. Rich org auth, billing, and branding controls live in the newer stack.
          </p>
        </div>
      </div>
    </AdminShell>
  );
}
