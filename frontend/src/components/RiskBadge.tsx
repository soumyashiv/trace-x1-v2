const COLORS: Record<string, string> = {
  low: "bg-green-900 text-green-300 border border-green-700",
  medium: "bg-yellow-900 text-yellow-300 border border-yellow-700",
  high: "bg-orange-900 text-orange-300 border border-orange-700",
  critical: "bg-red-900 text-red-300 border border-red-700",
};

export default function RiskBadge({ level, score }: { level: string; score?: number }) {
  return (
    <span className={`badge ${COLORS[level] || "bg-slate-800 text-slate-300"}`}>
      {level.toUpperCase()}
      {typeof score === "number" ? ` · ${score.toFixed(1)}` : ""}
    </span>
  );
}
