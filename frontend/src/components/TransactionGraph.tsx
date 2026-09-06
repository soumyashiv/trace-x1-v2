"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MarkerType,
  Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { InvestigationResult } from "@/lib/api";

const RISK_COLOR: Record<string, string> = {
  low: "#16a34a",
  medium: "#ca8a04",
  high: "#ea580c",
  critical: "#dc2626",
};

export default function TransactionGraph({
  result,
  onSelectNode,
}: {
  result: InvestigationResult;
  onSelectNode?: (address: string) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const addresses = new Set<string>();
    result.timeline.forEach((e) => {
      addresses.add(e.from);
      addresses.add(e.to);
    });

    const riskByAddress: Record<string, string> = {
      [result.wallet_risk.address]: result.wallet_risk.risk_level,
    };
    result.intermediary_risks.forEach((r) => (riskByAddress[r.address] = r.risk_level));
    result.vasp_attributions.forEach((a) => {
      if (a.likely_entity) riskByAddress[a.target_address] = "high";
    });

    const addrList = Array.from(addresses);
    const nodes: Node[] = addrList.map((addr, i) => {
      const angle = (2 * Math.PI * i) / addrList.length;
      const radius = 260;
      const level = riskByAddress[addr];
      const isSource = addr === result.suspect_wallet;
      return {
        id: addr,
        position: {
          x: 400 + radius * Math.cos(angle),
          y: 300 + radius * Math.sin(angle),
        },
        data: { label: shorten(addr) },
        style: {
          background: isSource ? "#1d4ed8" : level ? RISK_COLOR[level] : "#334155",
          color: "white",
          border: "1px solid #0f172a",
          borderRadius: 8,
          fontSize: 11,
          padding: 6,
          width: 150,
        },
      };
    });

    const edges: Edge[] = result.timeline.map((e, i) => ({
      id: `${e.tx_hash}-${i}`,
      source: e.from,
      target: e.to,
      label: e.value.toFixed(2),
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#64748b" },
      labelStyle: { fill: "#cbd5e1", fontSize: 10 },
    }));

    return { nodes, edges };
  }, [result]);

  return (
    <div style={{ height: 520 }} className="rounded-xl overflow-hidden border border-slate-800">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(_, node) => onSelectNode?.(node.id)}
        fitView
      >
        <Background color="#1e293b" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function shorten(addr: string): string {
  if (addr.length <= 18) return addr;
  return `${addr.slice(0, 10)}…${addr.slice(-6)}`;
}
