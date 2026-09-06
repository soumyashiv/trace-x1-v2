import csv
import io
import json
import unittest

from app.core.demo_data import build_demo_case
from app.core.pipeline import run_investigation
from app.core.provider import MockBlockchainProvider
from app.core.report_service import generate_csv, generate_json, generate_pdf


class TestReportService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = build_demo_case("case-demo-001")
        cls.provider = MockBlockchainProvider()
        cls.result = run_investigation(cls.case.suspect_wallet, cls.provider)

    def test_generate_json_is_valid_and_complete(self):
        raw = generate_json(self.case, self.result)
        payload = json.loads(raw)
        for key in (
            "case",
            "suspect_wallet",
            "transaction_summary",
            "fund_flow_paths",
            "risk_score",
            "likely_vasp_attributions",
            "evidence",
            "recommendations",
            "limitations",
            "generated_at",
        ):
            self.assertIn(key, payload)
        self.assertGreater(payload["transaction_summary"]["total_transactions"], 0)

    def test_generate_json_never_claims_guarantee(self):
        raw = generate_json(self.case, self.result)
        lowered = raw.lower()
        for banned_phrase in ("guaranteed attribution", "100% confirmed", "guaranteed recovery"):
            self.assertNotIn(banned_phrase, lowered)
        self.assertIn("limitations", lowered)

    def test_generate_csv_has_header_and_rows(self):
        raw = generate_csv(self.case, self.result)
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
        self.assertEqual(
            rows[0],
            ["tx_hash", "from_address", "to_address", "value", "timestamp", "block_number", "fee"],
        )
        self.assertEqual(len(rows) - 1, len(self.result.transactions))

    def test_generate_pdf_produces_nonempty_bytes(self):
        pdf_bytes = generate_pdf(self.case, self.result)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        # PDF magic number
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
