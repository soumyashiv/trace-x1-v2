"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import NavBar from "@/components/NavBar";
import RiskBadge from "@/components/RiskBadge";
import TransactionGraph from "@/components/TransactionGraph";
import {
  CaseSummary,
  InvestigationResult,
  RiskResult,
  getCase,
  getLatestInvestigation,
  reportUrl,
  runInvestigation,
} from "@/lib/api";

type Tab = "graph" | "risk" | "vasp" | "evidence" | "timeline" | "report";

const TABS: { id: Tab; label: string }[] = [
  { id: "graph", label: "Transaction Graph" },
  { id: "risk", label: "Risk Analysis" },
  { id: "vasp", label: "VASP Attribution" },
  { id: "evidence", label: "Evidence" },
  { id: "timeline", label: "Timeline" },
  { id: "report", label: "Report" },
];

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = params.id as string;

  const [caseInfo, setCaseInfo] = useState<CaseSummary | null>(null);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [tab, setTab] = useState<Tab>("graph");
  const [selectedAddress, setSelectedAddress] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [c, r] = await Promise.all([getCase(caseId), getLatestInvestigation(caseId)]);
      setCaseInfo(c);
      setResult(r);
    } catch {
      setError("Could not load this case. Try re-running the investigation.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (caseId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  async function rerun() {
    setRerunning(true);
    try {
      const r = await runInvestigation(caseId);
      setResult(r);
    } finally {
      setRerunning(false);
    }
  }

  const selectedRisk: RiskResult | undefined = result
    ? [result.wallet_risk, ...result.intermediary_risks].find((r) => r.address === selectedAddress)
    : undefined;

  return (
    <div>
      <NavBar />
      <main className="max-w-6xl mx-auto p-6 space-y-6">
        {loading && <p className="text-slate-400 text-sm">Loading investigation…</p>}
        {error && <p className="text-red-400 text-sm">{error}</p>}

        {caseInfo && result && (
          <>
            <header className="flex items-start justify-between">
              <div>
                <h1 className="text-xl font-semibold">{caseInfo.title}</h1>
                <p className="text-sm text-slate-500 font-mono">{caseInfo.suspect_wallet}</p>
              </div>
              <div className="flex items-center gap-3">
                <RiskBadge level={result.wallet_risk.risk_level} score={result.wallet_risk.risk_score} />
                <button
                  onClick={rerun}
                  disabled={rerunning}
                  className="text-sm bg-slate-800 hover:bg-slate-700 rounded-md px-3 py-1.5 disabled:opacity-50"
                >
                  {rerunning ? "Re-tracing…" : "Re-run trace"}
                </button>
              </div>
            </header>

            <div className="card text-sm text-slate-300">{result.summary}</div>

            <nav className="flex gap-2 border-b border-slate-800 pb-2">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-3 py-1.5 rounded-md text-sm ${
                    tab === t.id ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </nav>

            {tab === "graph" && (
              <div className="space-y-4">
                <TransactionGraph result={result} onSelectNode={setSelectedAddress} />
                {selectedAddress && (
                  <div className="card">
                    <h3 className="font-medium mb-2">Wallet detail — {selectedAddress}</h3>
                    {selectedRisk ? (
                      <div className="space-y-2 text-sm">
                        <RiskBadge level={selectedRisk.risk_level} score={selectedRisk.risk_score} />
                        <ul className="list-disc list-inside text-slate-300">
                          {selectedRisk.evidence.map((e, i) => (
                            <li key={i}>{e}</li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400">
                        No individual risk score computed for this node (not flagged as an
                        intermediary or the suspect wallet).
                      </p>
                    )}
                  </div>
                )}
                {result.suspicious_paths.length > 0 && (
                  <div className="card">
                    <h3 className="font-medium mb-2">Suspicious fund-flow paths</h3>
                    {result.suspicious_paths.map((p, i) => (
                      <p key={i} className="text-xs font-mono text-slate-400 mb-1">
                        {p.join(" → ")}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}

            {tab === "risk" && (
              <div className="space-y-4">
                <RiskCard title="Suspect wallet" risk={result.wallet_risk} />
                {result.intermediary_risks.map((r) => (
                  <RiskCard key={r.address} title={r.address} risk={r} />
                ))}
              </div>
            )}

            {tab === "vasp" && (
              <div className="space-y-4">
                {result.vasp_attributions.map((a, i) => (
                  <div className="card" key={i}>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium">{a.likely_entity || "No confident match"}</h3>
                      <span className="badge bg-slate-800 text-slate-300">
                        confidence {(a.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-2">
                      Source: {a.source || "n/a"} · Last verified: {a.last_verified || "n/a"}
                    </p>
                    {a.supporting_evidence.length > 0 && (
                      <div className="mb-2">
                        <p className="text-xs text-slate-500 mb-1">Supporting evidence</p>
                        <ul className="list-disc list-inside text-sm text-slate-300">
                          {a.supporting_evidence.map((e, j) => (
                            <li key={j}>{e}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {a.contradicting_evidence.length > 0 && (
                      <div className="mb-2">
                        <p className="text-xs text-slate-500 mb-1">Contradicting evidence</p>
                        <ul className="list-disc list-inside text-sm text-orange-300">
                          {a.contradicting_evidence.map((e, j) => (
                            <li key={j}>{e}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <p className="text-xs text-slate-500 italic">{a.disclaimer}</p>
                  </div>
                ))}
              </div>
            )}

            {tab === "evidence" && (
              <div className="card">
                <h3 className="font-medium mb-2">Evidence log — suspect wallet</h3>
                <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
                  {result.wallet_risk.evidence.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            )}

            {tab === "timeline" && (
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-slate-500 text-left">
                    <tr>
                      <th className="pb-2 pr-4">Timestamp</th>
                      <th className="pb-2 pr-4">From</th>
                      <th className="pb-2 pr-4">To</th>
                      <th className="pb-2">Value</th>
                    </tr>
                  </thead>
                  <tbody className="font-mono text-xs text-slate-300">
                    {result.timeline.map((e, i) => (
                      <tr key={i} className="border-t border-slate-800">
                        <td className="py-2 pr-4">{new Date(e.timestamp).toLocaleString()}</td>
                        <td className="py-2 pr-4">{e.from.slice(0, 16)}…</td>
                        <td className="py-2 pr-4">{e.to.slice(0, 16)}…</td>
                        <td className="py-2">{e.value.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {tab === "report" && (
              <div className="card space-y-3">
                <h3 className="font-medium">Generate investigation report</h3>
                <p className="text-sm text-slate-400">
                  Includes suspect wallet, transaction summary, fund-flow path, risk score and
                  contributors, likely VASP, attribution confidence, evidence, recommendations, and
                  stated limitations.
                </p>
                <div className="flex gap-3">
                  <a
                    className="bg-red-600 hover:bg-red-500 rounded-md px-4 py-2 text-sm font-medium"
                    href={reportUrl(caseId, "pdf")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download PDF
                  </a>
                  <a
                    className="bg-slate-800 hover:bg-slate-700 rounded-md px-4 py-2 text-sm font-medium"
                    href={reportUrl(caseId, "json")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download JSON
                  </a>
                  <a
                    className="bg-slate-800 hover:bg-slate-700 rounded-md px-4 py-2 text-sm font-medium"
                    href={reportUrl(caseId, "csv")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download CSV
                  </a>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function RiskCard({ title, risk }: { title: string; risk: RiskResult }) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium font-mono text-sm">{title}</h3>
        <RiskBadge level={risk.risk_level} score={risk.risk_score} />
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        {Object.entries(risk.feature_contributions).map(([k, v]) => (
          <div key={k} className="flex justify-between text-xs bg-slate-800 rounded px-2 py-1">
            <span className="text-slate-400">{k.replace(/_/g, " ")}</span>
            <span className="font-mono">{v.toFixed(2)}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-500 mb-1">
        Confidence: {(risk.confidence * 100).toFixed(0)}%
      </p>
      <ul className="list-disc list-inside text-sm text-slate-300">
        {risk.evidence.map((e, i) => (
          <li key={i}>{e}</li>
        ))}
      </ul>
    </div>
  );
}
