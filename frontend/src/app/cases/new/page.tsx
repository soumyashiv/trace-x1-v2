"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import NavBar from "@/components/NavBar";
import { createCase, runInvestigation } from "@/lib/api";

const DEMO_WALLETS = [
  "0xVICTIM0000000000000000000000000000A1",
  "0xVICTIM0000000000000000000000000000B2",
];

export default function NewInvestigationPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [wallet, setWallet] = useState(DEMO_WALLETS[0]);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const created = await createCase({ title, suspect_wallet: wallet, chain: "MOCK", notes });
      await runInvestigation(created.case_id);
      router.push(`/cases/${created.case_id}`);
    } catch {
      setError("Could not create the case. Check the backend connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <NavBar />
      <main className="max-w-2xl mx-auto p-6">
        <h1 className="text-xl font-semibold mb-6">New Investigation</h1>
        <form onSubmit={handleSubmit} className="card space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Case title</label>
            <input
              required
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Reported investment scam — victim R. Sharma"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1">Victim-reported suspect wallet</label>
            <input
              required
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm font-mono"
              value={wallet}
              onChange={(e) => setWallet(e.target.value)}
            />
            <p className="text-xs text-slate-500 mt-1">
              Demo wallets:{" "}
              {DEMO_WALLETS.map((w) => (
                <button
                  type="button"
                  key={w}
                  onClick={() => setWallet(w)}
                  className="underline decoration-dotted mr-2 hover:text-slate-300"
                >
                  {w.slice(0, 14)}…
                </button>
              ))}
            </p>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1">Notes (optional)</label>
            <textarea
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-red-600 hover:bg-red-500 rounded-md py-2 text-sm font-medium disabled:opacity-50"
          >
            {loading ? "Tracing…" : "Create case & run trace"}
          </button>
        </form>
      </main>
    </div>
  );
}
