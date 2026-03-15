"use client";

import Link from "next/link";

export default function HomePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-blue-100">
      <div className="text-center max-w-2xl px-6">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          Agentic Demo Brain
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          AI-powered live product demo engine for B2B SaaS.
          Let buyers explore your product with a voice AI agent.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/admin"
            className="btn-primary text-lg px-8 py-3"
          >
            Admin Dashboard
          </Link>
          <Link
            href="/meet/demo-acme-crm-001"
            className="btn-secondary text-lg px-8 py-3"
          >
            Try Meeting V2
          </Link>
          <Link
            href="/demo/demo-acme-crm-001"
            className="btn-secondary text-lg px-8 py-3"
          >
            Legacy Demo
          </Link>
        </div>
        <div className="mt-12 text-sm text-gray-500">
          <p>Run <code className="bg-gray-200 px-2 py-0.5 rounded">make seed</code> first to populate sample data</p>
        </div>
      </div>
    </div>
  );
}
