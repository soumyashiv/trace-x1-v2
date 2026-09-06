import unittest

from app.core.pipeline import run_investigation
from app.core.provider import MockBlockchainProvider


class TestHappyPathPipeline(unittest.TestCase):
    """
    Integration test for the exact chain required by the spec:

        case -> wallet -> transactions -> graph -> suspicious path
             -> risk -> VASP hypothesis -> report

    This runs the full pipeline offline via MockBlockchainProvider, with
    no network access and no external services.
    """

    def setUp(self):
        self.wallet = "0xVICTIM0000000000000000000000000000A1"
        self.provider = MockBlockchainProvider()
        self.result = run_investigation(self.wallet, self.provider)

    def test_transactions_were_loaded(self):
        self.assertGreater(len(self.result.transactions), 0)

    def test_graph_derived_intermediaries_present(self):
        self.assertTrue(len(self.result.intermediaries) >= 1)

    def test_suspicious_path_reaches_known_exchange(self):
        self.assertTrue(len(self.result.suspicious_paths) >= 1)
        self.assertTrue(
            any(p[-1] == "0xEXCHANGE_KRAKENISH_HOT1" for p in self.result.suspicious_paths)
        )

    def test_wallet_risk_is_explainable(self):
        self.assertTrue(len(self.result.wallet_risk.evidence) >= 1)
        self.assertTrue(len(self.result.wallet_risk.feature_contributions) >= 1)

    def test_vasp_attribution_present_and_hedged(self):
        self.assertTrue(len(self.result.vasp_attributions) >= 1)
        top = self.result.vasp_attributions[0]
        self.assertIsNotNone(top.likely_entity)
        self.assertLess(top.confidence, 1.0)

    def test_full_result_serializes_cleanly(self):
        d = self.result.to_dict()
        self.assertIn("summary", d)
        self.assertIn("wallet_risk", d)
        self.assertIn("vasp_attributions", d)
        self.assertIsInstance(d["summary"], str)
        self.assertGreater(len(d["summary"]), 10)

    def test_deterministic_end_to_end(self):
        """Running the whole pipeline twice must produce the same graph
        shape and the same top VASP hypothesis — required for an
        offline demo that has to work identically every time."""
        result2 = run_investigation(self.wallet, MockBlockchainProvider())
        self.assertEqual(len(self.result.transactions), len(result2.transactions))
        self.assertEqual(
            self.result.vasp_attributions[0].target_address,
            result2.vasp_attributions[0].target_address,
        )
        self.assertAlmostEqual(
            self.result.wallet_risk.risk_score, result2.wallet_risk.risk_score, places=6
        )


if __name__ == "__main__":
    unittest.main()
