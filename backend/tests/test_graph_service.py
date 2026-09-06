import unittest

from app.core.graph_service import (
    build_graph,
    compute_hops,
    compute_wallet_stats,
    detect_intermediaries,
    edge_timeline,
    find_paths_to_labelled_nodes,
)
from app.core.provider import MockBlockchainProvider


class TestGraphService(unittest.TestCase):
    def setUp(self):
        self.wallet = "0xVICTIM0000000000000000000000000000A1"
        self.provider = MockBlockchainProvider()
        self.txs = self.provider.get_transactions(self.wallet)
        self.g = build_graph(self.txs)

    def test_graph_has_expected_node_and_edge_counts(self):
        self.assertGreater(self.g.number_of_nodes(), 3)
        self.assertEqual(self.g.number_of_edges(), len(self.txs))

    def test_source_wallet_is_root(self):
        hops = compute_hops(self.g, self.wallet)
        self.assertEqual(hops[self.wallet], 0)

    def test_exchange_is_reachable_with_multiple_hops(self):
        hops = compute_hops(self.g, self.wallet)
        self.assertIn("0xEXCHANGE_KRAKENISH_HOT1", hops)
        self.assertGreaterEqual(hops["0xEXCHANGE_KRAKENISH_HOT1"], 2)

    def test_burner_is_one_hop_from_source(self):
        hops = compute_hops(self.g, self.wallet)
        burner = f"0xBURNER_{self.wallet[-6:]}"
        self.assertEqual(hops[burner], 1)

    def test_detect_intermediaries_flags_pass_through_nodes(self):
        intermediaries = detect_intermediaries(self.g, self.wallet)
        burner = f"0xBURNER_{self.wallet[-6:]}"
        inter1 = f"0xINTER1_{self.wallet[-6:]}"
        self.assertIn(burner, intermediaries)
        self.assertIn(inter1, intermediaries)
        # the exchange is a sink (no outbound edges here), so should NOT
        # be flagged as an intermediary
        self.assertNotIn("0xEXCHANGE_KRAKENISH_HOT1", intermediaries)

    def test_find_paths_to_labelled_nodes(self):
        paths = find_paths_to_labelled_nodes(
            self.g, self.wallet, {"0xEXCHANGE_KRAKENISH_HOT1"}
        )
        self.assertTrue(len(paths) >= 1)
        for path in paths:
            self.assertEqual(path[0], self.wallet)
            self.assertEqual(path[-1], "0xEXCHANGE_KRAKENISH_HOT1")

    def test_wallet_stats_fan_metrics(self):
        stats = compute_wallet_stats(self.g, self.wallet)
        exchange_stats = stats["0xEXCHANGE_KRAKENISH_HOT1"]
        # exchange receives from two converging intermediaries -> fan_in >= 2
        self.assertGreaterEqual(exchange_stats.fan_in, 2)

    def test_edge_timeline_sorted_ascending(self):
        events = edge_timeline(self.g)
        timestamps = [e["timestamp"] for e in events]
        self.assertEqual(timestamps, sorted(timestamps))


if __name__ == "__main__":
    unittest.main()
