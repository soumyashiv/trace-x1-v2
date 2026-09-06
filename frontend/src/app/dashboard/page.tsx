"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import NavBar from "@/components/NavBar";
import { CaseSummary, listCases } from "@/lib/api";

export default function DashboardPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCases()
      .then(setCases)
      .catch(() => setError("Could not load cases. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <NavBar />
      <main className="max-w-6xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Case Dashboard</h1>
          <Link
            href="/cases/new"
            className="bg-red-600 hover:bg-red-500 rounded-md px-4 py-2 text-sm font-medium"
          >
            + New Investigation
          </Link>
        </div>

        {loading && <p className="text-slate-400 text-sm">Loading cases…</p>}
        {error && <p className="text-red-400 text-sm">{error}</p>}

        {!loading && !error && cases.length === 0 && (
          <div className="card text-slate-400 text-sm">
            No cases yet. Start your first investigation from a victim-reported wallet.
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cases.map((c) => (
            <Link key={c.case_id} href={`/cases/${c.case_id}`} className="card hover:border-slate-600">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs uppercase tracking-wide text-slate-500">{c.chain}</span>
                <span className="badge bg-slate-800 text-slate-300">{c.status}</span>
              </div>
              <h2 className="font-medium mb-1">{c.title}</h2>
              <p className="text-xs text-slate-500 font-mono break-all">{c.suspect_wallet}</p>
              <p className="text-xs text-slate-600 mt-3">
                Opened {new Date(c.created_at).toLocaleDateString()} · {c.investigator}
              </p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
