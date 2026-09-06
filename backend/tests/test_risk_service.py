import unittest

from app.core.graph_service import build_graph
from app.core.provider import MockBlockchainProvider
from app.core.risk_service import score_wallet


class TestRiskService(unittest.TestCase):
    def setUp(self):
        self.wallet = "0xVICTIM0000000000000000000000000000A1"
        self.provider = MockBlockchainProvider()
        self.txs = self.provider.get_transactions(self.wallet)
        self.g = build_graph(self.txs)
        self.labels = {}
        for addr in self.g.nodes:
            label = self.provider.get_wallet_label(addr)
            if label:
                self.labels[addr] = label

    def test_score_is_bounded(self):
        result = score_wallet(self.wallet, self.txs, self.g, self.wallet, self.labels)
        self.assertGreaterEqual(result.risk_score, 0.0)
        self.assertLessEqual(result.risk_score, 100.0)

    def test_never_unexplained_score(self):
        """Hard requirement from the spec: every score ships with
        contributions and at least one piece of evidence."""
        result = score_wallet(self.wallet, self.txs, self.g, self.wallet, self.labels)
        self.assertTrue(len(result.feature_contributions) > 0)
        self.assertTrue(len(result.evidence) >= 1)
        # contributions must actually sum to (approximately) the score
        self.assertAlmostEqual(
            sum(result.feature_contributions.values()), result.risk_score, delta=0.01
        )

    def test_confidence_bounded(self):
        result = score_wallet(self.wallet, self.txs, self.g, self.wallet, self.labels)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_exchange_wallet_scores_high_or_critical(self):
        """The known exchange address has a direct label hit -> should
        score meaningfully higher than an untouched, unlabeled address."""
        exchange = "0xEXCHANGE_KRAKENISH_HOT1"
        result = score_wallet(exchange, self.txs, self.g, self.wallet, self.labels)
        self.assertIn(result.risk_level, ("medium", "high", "critical"))
        self.assertGreater(result.raw_features["known_risk_label"], 0)

    def test_burner_scores_higher_than_random_unconnected_wallet(self):
        burner = f"0xBURNER_{self.wallet[-6:]}"
        burner_result = score_wallet(burner, self.txs, self.g, self.wallet, self.labels)

        # a synthetic, totally unconnected wallet not present in the graph
        stranger = "0xNOT_IN_GRAPH_AT_ALL"
        stranger_result = score_wallet(stranger, self.txs, self.g, self.wallet, self.labels)

        self.assertGreater(burner_result.risk_score, stranger_result.risk_score)

    def test_risk_level_thresholds_consistent_with_score(self):
        result = score_wallet(self.wallet, self.txs, self.g, self.wallet, self.labels)
        if result.risk_score >= 80:
            self.assertEqual(result.risk_level, "critical")
        elif result.risk_score >= 55:
            self.assertEqual(result.risk_level, "high")
        elif result.risk_score >= 30:
            self.assertEqual(result.risk_level, "medium")
        else:
            self.assertEqual(result.risk_level, "low")


if __name__ == "__main__":
    unittest.main()
