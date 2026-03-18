"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { api } from "@/lib/api";
import type { Workspace } from "@/types/api";

const EMPTY_PRODUCT = {
  name: "",
  description: "",
  product_url: "",
  allowed_domains: "",
  browser_auth_mode: "credentials",
};

function productState(product: Workspace) {
  if (product.is_active) return "Live";
  if (product.product_url) return "Configuring";
  return "Draft";
}

function formatDate(source?: string | null) {
  if (!source) return "Recently";
  const date = new Date(source);
  if (Number.isNaN(date.getTime())) return "Recently";
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function AdminProductsPage() {
  const [products, setProducts] = useState<Workspace[]>([]);
  const [sessionCounts, setSessionCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(EMPTY_PRODUCT);

  async function loadProducts() {
    try {
      const nextProducts = await api.listWorkspaces();
      setProducts(nextProducts);
      const counts = await Promise.all(
        nextProducts.map(async (product) => {
          try {
            const analytics = await api.getWorkspaceAnalytics(product.id);
            return [product.id, analytics.total_sessions] as const;
          } catch {
            return [product.id, 0] as const;
          }
        }),
      );
      setSessionCounts(Object.fromEntries(counts));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProducts();
  }, []);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    await api.createWorkspace({
      ...form,
      name: form.name.trim(),
      product_url: form.product_url.trim(),
      description: "",
    });
    setForm(EMPTY_PRODUCT);
    setShowCreate(false);
    await loadProducts();
  }

  const stats = useMemo(() => ({
    products: products.length,
    live: products.filter((product) => product.is_active).length,
  }), [products]);

  return (
    <AdminShell
      title="Products"
      description="Configure the products your AI agent demos, see which ones are live, and jump straight into setup or review."
      actions={<button onClick={() => setShowCreate((value) => !value)} className="btn-primary">{showCreate ? "Close" : "+ New"}</button>}
    >
      <section className="grid gap-4 md:grid-cols-2">
        <div className="admin-kpi rounded-[24px] px-5 py-4">
          <p className="admin-eyebrow">Products</p>
          <p className="mt-3 text-[2rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">{stats.products}</p>
        </div>
        <div className="admin-kpi rounded-[24px] px-5 py-4">
          <p className="admin-eyebrow">Live</p>
          <p className="mt-3 text-[2rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">{stats.live}</p>
        </div>
      </section>

      {showCreate ? (
        <form onSubmit={handleCreate} className="admin-panel rounded-[24px] px-5 py-5">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
            <div>
              <label className="mb-2 block text-sm text-[var(--text-primary)]">Product name</label>
              <input className="input" placeholder="Saleshandy" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
            </div>
            <div>
              <label className="mb-2 block text-sm text-[var(--text-primary)]">Website URL</label>
              <input className="input" placeholder="https://app.example.com" value={form.product_url} onChange={(event) => setForm({ ...form, product_url: event.target.value })} />
            </div>
            <div className="flex gap-3">
              <button type="submit" className="btn-primary">Create</button>
              <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </div>
        </form>
      ) : null}

      {loading ? (
        <div className="admin-panel rounded-[24px] px-5 py-6 text-sm text-[var(--text-secondary)]">Loading products...</div>
      ) : products.length === 0 ? (
        <div className="admin-empty px-8 py-14 text-center">
          <p className="admin-eyebrow">No products yet</p>
          <h2 className="mt-4 text-[2rem] font-medium tracking-[-0.04em] text-[var(--text-primary)]">Add your first product</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[var(--text-secondary)]">A product is the application you want the demo agent to walk through.</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary mt-6">+ New</button>
        </div>
      ) : (
        <section className="overflow-hidden rounded-[16px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.96)]">
          <div className="hidden grid-cols-[minmax(0,1.6fr)_minmax(180px,1fr)_120px_110px_140px] gap-4 px-5 py-3 text-xs uppercase tracking-[0.12em] text-[var(--text-tertiary)] md:grid">
            <span>Product</span>
            <span>URL</span>
            <span>State</span>
            <span>Sessions</span>
            <span>Last activity</span>
          </div>
          {products.map((product) => (
            <Link key={product.id} href={`/admin/products/${product.id}`} className="admin-table-row block px-5 py-4">
              <div className="grid gap-3 md:grid-cols-[minmax(0,1.6fr)_minmax(180px,1fr)_120px_110px_140px] md:items-center md:gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="h-2.5 w-2.5 rounded-full bg-[var(--accent-primary)]" />
                    <p className="text-[1.05rem] text-[var(--text-primary)]">{product.name}</p>
                  </div>
                  {product.description ? <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{product.description}</p> : null}
                </div>
                <div className="text-sm text-[var(--text-secondary)]">{product.product_url || "Not set yet"}</div>
                <div><span className="badge">{productState(product)}</span></div>
                <div className="text-sm text-[var(--text-secondary)]">{sessionCounts[product.id] ?? 0}</div>
                <div className="text-sm text-[var(--text-secondary)]">{formatDate(product.updated_at)}</div>
              </div>
            </Link>
          ))}
        </section>
      )}
    </AdminShell>
  );
}
