import unittest

from app.core.provider import (
    EVMBlockchainProvider,
    MockBlockchainProvider,
    ProviderUnavailableError,
)


class TestMockBlockchainProvider(unittest.TestCase):
    def setUp(self):
        self.provider = MockBlockchainProvider()
        self.wallet = "0xVICTIM0000000000000000000000000000A1"

    def test_is_healthy(self):
        self.assertTrue(self.provider.is_healthy())

    def test_deterministic_across_calls(self):
        txs1 = self.provider.get_transactions(self.wallet)
        txs2 = self.provider.get_transactions(self.wallet)
        self.assertEqual([t.tx_hash for t in txs1], [t.tx_hash for t in txs2])

    def test_deterministic_across_new_instances(self):
        txs1 = self.provider.get_transactions(self.wallet)
        fresh_provider = MockBlockchainProvider()
        txs2 = fresh_provider.get_transactions(self.wallet)
        self.assertEqual([t.tx_hash for t in txs1], [t.tx_hash for t in txs2])

    def test_different_wallets_get_different_graphs(self):
        txs_a = self.provider.get_transactions("0xWALLET_AAAAAA")
        txs_b = self.provider.get_transactions("0xWALLET_BBBBBB")
        self.assertNotEqual(
            {t.tx_hash for t in txs_a}, {t.tx_hash for t in txs_b}
        )

    def test_contains_expected_fund_flow_shape(self):
        txs = self.provider.get_transactions(self.wallet)
        froms = {t.from_address for t in txs}
        tos = {t.to_address for t in txs}
        # victim wallet must appear as a sender
        self.assertIn(self.wallet, froms)
        # a known exchange cluster address must appear as a receiver somewhere
        self.assertIn("0xEXCHANGE_KRAKENISH_HOT1", tos)

    def test_known_label_lookup(self):
        label = self.provider.get_wallet_label("0xEXCHANGE_KRAKENISH_HOT1")
        self.assertIsNotNone(label)
        self.assertEqual(label.label, "known_exchange")

    def test_unknown_label_lookup_returns_none(self):
        self.assertIsNone(self.provider.get_wallet_label("0xNOTHING_HERE"))

    def test_respects_limit(self):
        txs = self.provider.get_transactions(self.wallet, limit=2)
        self.assertLessEqual(len(txs), 2)


class TestEVMBlockchainProviderFailsHonestly(unittest.TestCase):
    def setUp(self):
        # ensure no env credentials leak into this test
        import os

        for var in ("TRACEX_EVM_RPC_URL", "TRACEX_EXPLORER_API_KEY"):
            os.environ.pop(var, None)
        self.provider = EVMBlockchainProvider()

    def test_unconfigured_provider_reports_unhealthy(self):
        self.assertFalse(self.provider.is_healthy())

    def test_unconfigured_provider_raises_not_fabricates(self):
        with self.assertRaises(ProviderUnavailableError):
            self.provider.get_transactions("0xSomeRealAddress")

    def test_unconfigured_label_lookup_raises(self):
        with self.assertRaises(ProviderUnavailableError):
            self.provider.get_wallet_label("0xSomeRealAddress")


if __name__ == "__main__":
    unittest.main()
