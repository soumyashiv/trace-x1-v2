"use client";

import { useEffect, useState } from "react";
import NavBar from "@/components/NavBar";
import { getSystemHealth } from "@/lib/api";

export default function SettingsPage() {
  const [health, setHealth] = useState<Record<string, boolean> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSystemHealth()
      .then(setHealth)
      .catch(() => setError("Could not reach the backend."));
  }, []);

  return (
    <div>
      <NavBar />
      <main className="max-w-3xl mx-auto p-6 space-y-6">
        <h1 className="text-xl font-semibold">Settings & System Health</h1>

        <div className="card">
          <h2 className="font-medium mb-3">Component status</h2>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          {health && (
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(health).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between bg-slate-800 rounded px-3 py-2 text-sm">
                  <span className="text-slate-300">{k.replace(/_/g, " ")}</span>
                  <span className={v ? "text-green-400" : "text-red-400"}>{v ? "OK" : "DOWN"}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card text-sm text-slate-400 space-y-2">
          <h2 className="font-medium text-slate-200">Data sources in this build</h2>
          <p>
            Blockchain data currently comes from the deterministic <b>mock provider</b> so the
            demo works fully offline. A real EVM provider adapter exists (see
            <code className="mx-1 text-slate-300">EVMBlockchainProvider</code>) but requires an
            RPC URL and explorer API key to be configured server-side.
          </p>
          <p>
            NCRP and SAHYOG integrations are mock connectors with documented interfaces — no live
            government API access is claimed or implemented in this prototype.
          </p>
        </div>
      </main>
    </div>
  );
}
