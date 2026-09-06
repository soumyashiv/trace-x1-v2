import unittest

from app.core.graph_service import build_graph
from app.core.provider import MockBlockchainProvider
from app.core.vasp_service import attribute_destination


class TestVaspService(unittest.TestCase):
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

    def test_finds_known_exchange(self):
        results = attribute_destination(self.g, self.wallet, self.labels)
        self.assertTrue(any(r.likely_entity for r in results))
        top = results[0]
        self.assertEqual(top.target_address, "0xEXCHANGE_KRAKENISH_HOT1")

    def test_never_asserts_certainty(self):
        """Hard requirement: confidence must never be exactly 1.0 (i.e.
        'guaranteed'), and every positive match carries supporting evidence
        plus the standard hedging disclaimer."""
        results = attribute_destination(self.g, self.wallet, self.labels)
        for r in results:
            self.assertLess(r.confidence, 1.0)
            if r.likely_entity:
                self.assertTrue(len(r.supporting_evidence) > 0)
            d = r.to_dict()
            self.assertIn("not a confirmed", d["disclaimer"])

    def test_no_match_case_is_explicit_not_fabricated(self):
        empty_labels = {}
        results = attribute_destination(self.g, self.wallet, empty_labels)
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0].likely_entity)
        self.assertEqual(results[0].confidence, 0.0)
        self.assertTrue(len(results[0].contradicting_evidence) > 0)

    def test_unreachable_source_returns_empty(self):
        results = attribute_destination(self.g, "0xADDRESS_NOT_IN_GRAPH", self.labels)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
