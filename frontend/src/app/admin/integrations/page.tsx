"use client";

import { AdminShell } from "@/components/admin-shell";

export default function AdminIntegrationsPage() {
  return (
    <AdminShell
      title="Integrations"
      description="Legacy demobase does not expose direct CRM or webhook setup yet, but this is where those connections will live."
    >
      <div className="admin-panel rounded-[16px] px-5 py-5">
        <p className="admin-eyebrow">Current state</p>
        <p className="mt-4 admin-note">
          The legacy control plane still keeps integrations inside backend environment configuration. This page reserves the IA slot required by the new admin spec and gives the future feature a stable home in the sidebar.
        </p>
      </div>
    </AdminShell>
  );
}
