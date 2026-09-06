import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("tracex_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export interface CaseSummary {
  case_id: string;
  title: string;
  investigator: string;
  suspect_wallet: string;
  chain: string;
  status: string;
  created_at: string;
}

export interface RiskResult {
  address: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  feature_contributions: Record<string, number>;
  raw_features: Record<string, number>;
  evidence: string[];
  confidence: number;
}

export interface VaspAttribution {
  target_address: string;
  likely_entity: string | null;
  confidence: number;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  last_verified: string | null;
  source: string | null;
  disclaimer: string;
}

export interface InvestigationResult {
  suspect_wallet: string;
  transaction_count: number;
  intermediaries: string[];
  suspicious_paths: string[][];
  wallet_risk: RiskResult;
  intermediary_risks: RiskResult[];
  vasp_attributions: VaspAttribution[];
  timeline: { tx_hash: string; from: string; to: string; value: number; timestamp: string }[];
  generated_at: string;
  summary: string;
}

export async function login(username: string, password: string) {
  const { data } = await api.post("/auth/login", { username, password });
  return data as { access_token: string; role: string };
}

export async function createCase(payload: {
  title: string;
  suspect_wallet: string;
  chain?: string;
  notes?: string;
}) {
  const { data } = await api.post("/cases", payload);
  return data as CaseSummary;
}

export async function listCases() {
  const { data } = await api.get("/cases");
  return data as CaseSummary[];
}

export async function getCase(caseId: string) {
  const { data } = await api.get(`/cases/${caseId}`);
  return data as CaseSummary;
}

export async function runInvestigation(caseId: string, txLimit = 500) {
  const { data } = await api.post(`/cases/${caseId}/investigation/run`, {
    tx_limit: txLimit,
  });
  return data as InvestigationResult;
}

export async function getLatestInvestigation(caseId: string) {
  const { data } = await api.get(`/cases/${caseId}/investigation/latest`);
  return data as InvestigationResult;
}

export async function getSystemHealth() {
  const { data } = await api.get("/system/health");
  return data;
}

export function reportUrl(caseId: string, format: "json" | "csv" | "pdf") {
  return `${API_BASE_URL}/cases/${caseId}/report.${format}`;
}
