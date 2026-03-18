"use client";

import Link from "next/link";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { usePathname, useRouter } from "next/navigation";

import { api } from "@/lib/api";
import type { Workspace } from "@/types/api";

type AdminShellProps = {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
};

type AdminWorkspaceContextValue = {
  workspaces: Workspace[];
  selectedWorkspaceId: string | null;
  selectedWorkspace: Workspace | null;
  setSelectedWorkspaceId: (workspaceId: string) => void;
};

type NavItem = {
  href: string;
  label: string;
  section: string;
  icon: string;
  matches: (pathname: string | null) => boolean;
};

const FILTERED_ROUTES = new Set([
  "/admin",
  "/admin/sessions",
  "/admin/contacts",
  "/admin/analytics",
  "/admin/keywords",
  "/admin/intent",
]);

const NAV_ITEMS: NavItem[] = [
  {
    href: "/admin",
    label: "Dashboard",
    section: "Workspace",
    icon: "dashboard",
    matches: (pathname) => pathname === "/admin",
  },
  {
    href: "/admin/products",
    label: "Products",
    section: "Workspace",
    icon: "products",
    matches: (pathname) =>
      pathname === "/admin/products" ||
      pathname?.startsWith("/admin/products/") === true ||
      pathname?.startsWith("/admin/workspaces/") === true,
  },
  {
    href: "/admin/sessions",
    label: "Sessions",
    section: "Workspace",
    icon: "sessions",
    matches: (pathname) => pathname === "/admin/sessions" || pathname?.startsWith("/admin/sessions/") === true,
  },
  {
    href: "/admin/contacts",
    label: "Contacts",
    section: "Workspace",
    icon: "contacts",
    matches: (pathname) => pathname === "/admin/contacts",
  },
  {
    href: "/admin/analytics",
    label: "Analytics",
    section: "Intelligence",
    icon: "analytics",
    matches: (pathname) => pathname === "/admin/analytics",
  },
  {
    href: "/admin/keywords",
    label: "Keywords & Topics",
    section: "Intelligence",
    icon: "keywords",
    matches: (pathname) => pathname === "/admin/keywords",
  },
  {
    href: "/admin/intent",
    label: "Intent Signals",
    section: "Intelligence",
    icon: "intent",
    matches: (pathname) => pathname === "/admin/intent",
  },
  {
    href: "/admin/settings",
    label: "Settings",
    section: "Configure",
    icon: "settings",
    matches: (pathname) => pathname === "/admin/settings",
  },
  {
    href: "/admin/integrations",
    label: "Integrations",
    section: "Configure",
    icon: "integrations",
    matches: (pathname) => pathname === "/admin/integrations",
  },
  {
    href: "/admin/help",
    label: "Help",
    section: "Configure",
    icon: "help",
    matches: (pathname) => pathname === "/admin/help",
  },
];

const AdminWorkspaceContext = createContext<AdminWorkspaceContextValue | null>(null);

function Icon({ name, active }: { name: string; active: boolean }) {
  const color = active ? "var(--text-primary)" : "var(--text-secondary)";

  const paths: Record<string, React.ReactNode> = {
    dashboard: (
      <>
        <path d="M3.75 4.5H10.5V10.5H3.75z" />
        <path d="M12.75 4.5H19.5V8.25H12.75z" />
        <path d="M12.75 10.5H19.5V19.5H12.75z" />
        <path d="M3.75 12.75H10.5V19.5H3.75z" />
      </>
    ),
    products: (
      <>
        <path d="M4.5 6.75h15" />
        <path d="M4.5 12h15" />
        <path d="M4.5 17.25h15" />
        <path d="M7.5 4.5v15" />
      </>
    ),
    sessions: (
      <>
        <rect x="4.5" y="5.25" width="15" height="13.5" rx="2.25" />
        <path d="M8.25 9h7.5" />
        <path d="M8.25 12.75h7.5" />
        <path d="M8.25 16.5h4.5" />
      </>
    ),
    contacts: (
      <>
        <path d="M8.25 10.125a2.625 2.625 0 1 0 0-5.25 2.625 2.625 0 0 0 0 5.25Z" />
        <path d="M15.75 9.375a2.25 2.25 0 1 0 0-4.5 2.25 2.25 0 0 0 0 4.5Z" />
        <path d="M4.875 18c0-2.071 1.678-3.75 3.75-3.75h1.5A3.75 3.75 0 0 1 13.875 18" />
        <path d="M14.25 18c0-1.657 1.343-3 3-3h.75A3 3 0 0 1 21 18" />
      </>
    ),
    analytics: (
      <>
        <path d="M5.25 18.75V10.5" />
        <path d="M12 18.75V5.25" />
        <path d="M18.75 18.75v-6.75" />
      </>
    ),
    keywords: (
      <>
        <path d="M5.25 8.25h13.5" />
        <path d="M5.25 12h9.75" />
        <path d="M5.25 15.75h7.5" />
        <path d="m15.75 13.5 3.75 3.75" />
      </>
    ),
    intent: (
      <>
        <path d="M12 19.5c4.142 0 7.5-3.358 7.5-7.5S16.142 4.5 12 4.5 4.5 7.858 4.5 12s3.358 7.5 7.5 7.5Z" />
        <path d="m12 12 3.75-3.75" />
        <path d="M12 8.25V12h3.75" />
      </>
    ),
    settings: (
      <>
        <path d="M12 8.625a3.375 3.375 0 1 0 0 6.75 3.375 3.375 0 0 0 0-6.75Z" />
        <path d="M19.125 12a7.143 7.143 0 0 0-.09-1.095l1.89-1.47-1.8-3.12-2.28.705a7.36 7.36 0 0 0-1.89-1.095L14.625 3h-3.75l-.33 2.925a7.36 7.36 0 0 0-1.89 1.095l-2.28-.705-1.8 3.12 1.89 1.47a7.143 7.143 0 0 0 0 2.19l-1.89 1.47 1.8 3.12 2.28-.705a7.36 7.36 0 0 0 1.89 1.095l.33 2.925h3.75l.33-2.925a7.36 7.36 0 0 0 1.89-1.095l2.28.705 1.8-3.12-1.89-1.47c.06-.36.09-.726.09-1.095Z" />
      </>
    ),
    integrations: (
      <>
        <path d="M8.25 8.25 5.25 12l3 3.75" />
        <path d="M15.75 8.25 18.75 12l-3 3.75" />
        <path d="M10.875 18.75 13.125 5.25" />
      </>
    ),
    help: (
      <>
        <path d="M9.375 9.375a2.625 2.625 0 1 1 5.25 0c0 1.875-2.625 2.25-2.625 4.125" />
        <path d="M12 18h.008" />
        <path d="M12 20.25c4.556 0 8.25-3.694 8.25-8.25S16.556 3.75 12 3.75 3.75 7.444 3.75 12s3.694 8.25 8.25 8.25Z" />
      </>
    ),
  };

  return (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}

function buildHref(pathname: string | null, searchParams: URLSearchParams | null, workspaceId: string) {
  if (!pathname) return "/admin";
  if (pathname.startsWith("/admin/products/")) {
    return `/admin/products/${workspaceId}`;
  }
  if (!FILTERED_ROUTES.has(pathname)) {
    return pathname;
  }
  const nextParams = new URLSearchParams(searchParams?.toString() ?? "");
  nextParams.set("workspaceId", workspaceId);
  const query = nextParams.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export function useAdminWorkspace() {
  const context = useContext(AdminWorkspaceContext);
  if (!context) {
    throw new Error("useAdminWorkspace must be used inside AdminShell");
  }
  return context;
}

export function AdminShell({ title, description, actions, children }: AdminShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [preferredWorkspaceId, setPreferredWorkspaceId] = useState<string | null>(null);
  const [searchString, setSearchString] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    setSearchString(window.location.search);
  }, [pathname]);

  useEffect(() => {
    try {
      setPreferredWorkspaceId(window.localStorage.getItem("demobase-admin-workspace"));
    } catch {
      setPreferredWorkspaceId(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadWorkspaces() {
      const items = await api.listWorkspaces();
      if (!cancelled) {
        setWorkspaces(items);
      }
    }
    void loadWorkspaces();
    return () => {
      cancelled = true;
    };
  }, []);

  const routeWorkspaceId = useMemo(() => {
    if (!pathname?.startsWith("/admin/products/")) return null;
    return pathname.split("/")[3] ?? null;
  }, [pathname]);

  const searchParams = useMemo(() => new URLSearchParams(searchString), [searchString]);
  const queryWorkspaceId = searchParams?.get("workspaceId") ?? null;
  const selectedWorkspaceId =
    routeWorkspaceId ?? queryWorkspaceId ?? preferredWorkspaceId ?? workspaces[0]?.id ?? null;
  const selectedWorkspace =
    workspaces.find((workspace) => workspace.id === selectedWorkspaceId) ?? null;

  useEffect(() => {
    if (!selectedWorkspaceId) return;
    try {
      window.localStorage.setItem("demobase-admin-workspace", selectedWorkspaceId);
    } catch {
      // Ignore local storage failures in restricted environments.
    }
  }, [selectedWorkspaceId]);

  useEffect(() => {
    if (!pathname || routeWorkspaceId || queryWorkspaceId || !selectedWorkspaceId) return;
    if (!FILTERED_ROUTES.has(pathname)) return;
    router.replace(buildHref(pathname, searchParams, selectedWorkspaceId));
  }, [pathname, routeWorkspaceId, queryWorkspaceId, router, searchParams, selectedWorkspaceId]);

  const groupedItems = useMemo(() => {
    return ["Workspace", "Intelligence", "Configure"].map((section) => ({
      section,
      items: NAV_ITEMS.filter((item) => item.section === section),
    }));
  }, []);

  const contextValue = useMemo<AdminWorkspaceContextValue>(
    () => ({
      workspaces,
      selectedWorkspaceId,
      selectedWorkspace,
      setSelectedWorkspaceId: (workspaceId: string) => {
        setPreferredWorkspaceId(workspaceId);
        router.push(buildHref(pathname, searchParams, workspaceId));
      },
    }),
    [pathname, router, searchParams, selectedWorkspace, selectedWorkspaceId, workspaces],
  );

  return (
    <AdminWorkspaceContext.Provider value={contextValue}>
      <div className="admin-theme min-h-screen">
        <div className="mx-auto max-w-[1500px] px-4 py-4 lg:px-6 lg:py-5">
          <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
            <aside className="admin-sidebar lg:sticky lg:top-5 lg:h-[calc(100vh-2.5rem)]">
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between px-3 py-2">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-[12px] bg-[var(--surface-accent)] text-sm font-medium text-[var(--accent-primary)]">
                      D
                    </div>
                    <div>
                      <p className="text-sm text-[var(--text-primary)]">DemoAgent</p>
                    </div>
                  </div>
                  <button type="button" className="admin-command-pill" aria-label="Command palette shortcut">
                    ⌘K
                  </button>
                </div>

                <nav className="mt-6 space-y-5">
                  {groupedItems.map((group) => (
                    <div key={group.section}>
                      <p className="admin-eyebrow px-3">{group.section}</p>
                      <div className="mt-2 space-y-1">
                        {group.items.map((item) => {
                          const active = item.matches(pathname);
                          return (
                            <Link
                              key={item.href}
                              href={selectedWorkspaceId && FILTERED_ROUTES.has(item.href) ? buildHref(item.href, searchParams, selectedWorkspaceId) : item.href}
                              className="admin-nav-link"
                              data-active={active ? "true" : "false"}
                            >
                              <Icon name={item.icon} active={active} />
                              <span>{item.label}</span>
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </nav>

                <div className="mt-auto space-y-4 border-t border-[var(--border-subtle)] pt-4">
                  <div className="space-y-2">
                    <p className="admin-eyebrow px-3">Product context</p>
                    <div className="rounded-[12px] border border-[var(--border-subtle)] bg-[var(--surface-overlay)] px-3 py-3">
                      <label className="mb-2 block text-sm text-[var(--text-secondary)]" htmlFor="product-switcher">
                        Selected product
                      </label>
                      <select
                        id="product-switcher"
                        className="input"
                        value={selectedWorkspaceId ?? ""}
                        onChange={(event) => contextValue.setSelectedWorkspaceId(event.target.value)}
                      >
                        {workspaces.map((workspace) => (
                          <option key={workspace.id} value={workspace.id}>
                            {workspace.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center justify-between px-3 py-2">
                    <div>
                      <p className="text-sm text-[var(--text-primary)]">DemoBase Org</p>
                      <p className="text-sm text-[var(--text-secondary)]">Legacy workspace compatibility</p>
                    </div>
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--surface-accent)] text-sm text-[var(--accent-primary)]">
                      M
                    </div>
                  </div>
                </div>
              </div>
            </aside>

            <main className="min-w-0">
              <header className="admin-header">
                <div className="min-w-0">
                  <h1 className="text-[2.4rem] leading-none tracking-[-0.05em] text-[var(--text-primary)] sm:text-[2.85rem]">
                    {title}
                  </h1>
                  {description ? (
                    <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[var(--text-secondary)]">
                      {description}
                    </p>
                  ) : null}
                </div>
                {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
              </header>
              <div className="mt-6 space-y-4">{children}</div>
            </main>
          </div>
        </div>
      </div>
    </AdminWorkspaceContext.Provider>
  );
}
