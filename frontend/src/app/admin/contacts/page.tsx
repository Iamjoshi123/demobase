"use client";

import { AdminShell, useAdminWorkspace } from "@/components/admin-shell";
import { deriveContacts, formatRelativeTime } from "@/lib/admin-reporting";
import { useWorkspaceReportBundle } from "@/lib/use-workspace-report-bundle";

function ContactsContent() {
  const { selectedWorkspaceId } = useAdminWorkspace();
  const { bundle, loading, error } = useWorkspaceReportBundle(selectedWorkspaceId);

  if (loading && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">Loading contacts…</div>;
  }

  if (error && !bundle) {
    return <div className="admin-empty px-6 py-12 text-sm text-[var(--text-secondary)]">{error}</div>;
  }

  if (!bundle) return null;

  const contacts = deriveContacts(bundle.reports);

  return (
    <div className="admin-panel rounded-[16px] px-5 py-5">
      <p className="admin-eyebrow">Contacts</p>
      <div className="mt-4 space-y-3">
        {contacts.length > 0 ? contacts.map((contact) => (
          <div key={contact.label} className="admin-list-item">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm text-[var(--text-primary)]">{contact.label}</p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  {contact.sessions} sessions · Last seen {formatRelativeTime(contact.lastSeen)}
                </p>
              </div>
              <p className="text-sm text-[var(--text-secondary)]">{contact.averageIntent}/100</p>
            </div>
            {contact.interests.length > 0 ? (
              <p className="mt-3 text-sm text-[var(--text-secondary)]">Interested in: {contact.interests.join(", ")}</p>
            ) : null}
          </div>
        )) : <p className="text-sm text-[var(--text-secondary)]">No contact patterns available yet.</p>}
      </div>
    </div>
  );
}

export default function AdminContactsPage() {
  return (
    <AdminShell
      title="Contacts"
      description="A lightweight view of recurring prospect activity, even when sessions stay mostly anonymous."
    >
      <ContactsContent />
    </AdminShell>
  );
}
