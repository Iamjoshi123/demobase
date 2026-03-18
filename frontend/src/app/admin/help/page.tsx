"use client";

import { AdminShell } from "@/components/admin-shell";

export default function AdminHelpPage() {
  return (
    <AdminShell
      title="Help"
      description="Quick orientation for the legacy workspace stack and where to fix the most common issues."
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Docs</p>
          <p className="mt-4 admin-note">
            Product setup lives in Products. Session review and knowledge gaps live in Sessions. Intelligence pages derive from the same session summaries, so fixing gaps in product knowledge improves reports over time.
          </p>
        </div>
        <div className="admin-panel rounded-[16px] px-5 py-5">
          <p className="admin-eyebrow">Support</p>
          <p className="mt-4 admin-note">
            For local issues, check the backend health endpoint and the seeded workspace data first. This stack is intentionally compatibility-first, so some richer org features remain unavailable here.
          </p>
        </div>
      </div>
    </AdminShell>
  );
}
