"""
Generates the investigation report in JSON, CSV, and PDF formats.

PDF generation uses reportlab directly (no heavyweight templating engine)
so the report service has no framework dependency beyond that single
well-established library, keeping it testable in isolation.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.models import Case
from app.core.pipeline import InvestigationResult


def build_report_payload(case: Case, result: InvestigationResult) -> dict:
    """The single source of truth every export format is derived from."""
    return {
        "case": {
            "case_id": case.case_id,
            "title": case.title,
            "investigator": case.investigator,
            "status": case.status,
            "created_at": case.created_at.isoformat(),
        },
        "suspect_wallet": case.suspect_wallet,
        "transaction_summary": {
            "total_transactions": len(result.transactions),
            "total_value_out": round(
                sum(t.value for t in result.transactions if t.from_address == case.suspect_wallet),
                8,
            ),
            "distinct_addresses_involved": len(
                {t.from_address for t in result.transactions}
                | {t.to_address for t in result.transactions}
            ),
        },
        "fund_flow_paths": result.suspicious_paths,
        "risk_score": result.wallet_risk.to_dict(),
        "likely_vasp_attributions": [a.to_dict() for a in result.vasp_attributions],
        "evidence": result.wallet_risk.evidence,
        "recommendations": _recommendations(result),
        "limitations": [
            "This attribution is a data-driven hypothesis, not a confirmed "
            "identification, and is not admissible as sole evidence.",
            "Fund tracing cannot be guaranteed complete through unresolved "
            "mixers, cross-chain bridges, or privacy-preserving protocols.",
            "No live connection to NCRP/SAHYOG was used; integration "
            "adapters are mocked pending credentialed government API access.",
        ],
        "generated_at": result.generated_at.isoformat(),
    }


def _recommendations(result: InvestigationResult) -> list[str]:
    recs = []
    if result.wallet_risk.risk_level in ("high", "critical"):
        recs.append(
            "Prioritize this case for expedited investigation given the "
            f"{result.wallet_risk.risk_level} risk classification."
        )
    if result.vasp_attributions and result.vasp_attributions[0].likely_entity:
        top = result.vasp_attributions[0]
        recs.append(
            f"Issue a preservation/production request to {top.likely_entity} "
            f"for KYC records on the receiving deposit address "
            f"(attribution confidence {top.confidence*100:.0f}%)."
        )
    if result.intermediaries:
        recs.append(
            f"Flag intermediary wallet(s) {', '.join(result.intermediaries)} "
            "for cross-case correlation — reused laundering infrastructure "
            "often recurs across victims."
        )
    if not recs:
        recs.append(
            "No high-confidence lead was identified in this trace; consider "
            "requesting additional off-chain evidence (exchange KYC, IP logs) "
            "from the reporting victim."
        )
    return recs


def generate_json(case: Case, result: InvestigationResult) -> str:
    return json.dumps(build_report_payload(case, result), indent=2, default=str)


def generate_csv(case: Case, result: InvestigationResult) -> str:
    """One row per transaction — the raw evidentiary ledger."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["tx_hash", "from_address", "to_address", "value", "timestamp", "block_number", "fee"]
    )
    for tx in sorted(result.transactions, key=lambda t: t.timestamp):
        writer.writerow(
            [tx.tx_hash, tx.from_address, tx.to_address, tx.value, tx.timestamp.isoformat(), tx.block_number, tx.fee]
        )
    return buf.getvalue()


def generate_pdf(case: Case, result: InvestigationResult) -> bytes:
    """Render the professional investigation report as PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.grey)

    payload = build_report_payload(case, result)
    story = []

    story.append(Paragraph("TRACE-X Investigation Report", h1))
    story.append(Paragraph(f"Case: {case.title} ({case.case_id})", body))
    story.append(Paragraph(f"Investigator: {case.investigator}", body))
    story.append(Paragraph(f"Generated: {payload['generated_at']}", small))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Suspect Wallet", h2))
    story.append(Paragraph(case.suspect_wallet, body))

    story.append(Paragraph("Transaction Summary", h2))
    ts = payload["transaction_summary"]
    story.append(
        Paragraph(
            f"Total transactions traced: {ts['total_transactions']} &nbsp;|&nbsp; "
            f"Distinct addresses involved: {ts['distinct_addresses_involved']} &nbsp;|&nbsp; "
            f"Total value out from suspect wallet: {ts['total_value_out']}",
            body,
        )
    )

    story.append(Paragraph("Fund-Flow Path(s)", h2))
    if payload["fund_flow_paths"]:
        for path in payload["fund_flow_paths"]:
            story.append(Paragraph(" &rarr; ".join(path), body))
    else:
        story.append(Paragraph("No path to a labelled entity was found in this trace.", body))

    story.append(Paragraph("Risk Score", h2))
    rs = payload["risk_score"]
    story.append(
        Paragraph(
            f"Score: {rs['risk_score']} / 100 &nbsp;&mdash;&nbsp; "
            f"Level: {rs['risk_level'].upper()} &nbsp;&mdash;&nbsp; "
            f"Confidence: {rs['confidence']}",
            body,
        )
    )
    contrib_rows = [["Feature", "Contribution (of 100)"]] + [
        [k, str(v)] for k, v in rs["feature_contributions"].items()
    ]
    t = Table(contrib_rows, colWidths=[8 * cm, 6 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Evidence:", body))
    for ev in payload["evidence"]:
        story.append(Paragraph(f"&bull; {ev}", body))

    story.append(Paragraph("Likely VASP Attribution", h2))
    for attr in payload["likely_vasp_attributions"][:3]:
        entity = attr["likely_entity"] or "No match found"
        story.append(
            Paragraph(
                f"<b>{entity}</b> — confidence {attr['confidence']*100:.0f}% "
                f"(source: {attr['source'] or 'n/a'}, last verified: {attr['last_verified'] or 'n/a'})",
                body,
            )
        )
        for s in attr["supporting_evidence"]:
            story.append(Paragraph(f"&nbsp;&nbsp;+ {s}", small))
        for c in attr["contradicting_evidence"]:
            story.append(Paragraph(f"&nbsp;&nbsp;- {c}", small))
        story.append(Paragraph(attr["disclaimer"], small))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph("Recommendations", h2))
    for r in payload["recommendations"]:
        story.append(Paragraph(f"&bull; {r}", body))

    story.append(Paragraph("Limitations & Uncertainty", h2))
    for l in payload["limitations"]:
        story.append(Paragraph(f"&bull; {l}", body))

    doc.build(story)
    return buf.getvalue()
