import unittest

from app.core.integrations import MockNcrpConnector, MockSahyogConnector


class TestMockIntegrations(unittest.TestCase):
    def setUp(self):
        self.ncrp = MockNcrpConnector()
        self.sahyog = MockSahyogConnector()

    def test_ncrp_fetch_known_prefix(self):
        ref = self.ncrp.fetch_complaint("NCRP-12345")
        self.assertIsNotNone(ref)
        self.assertEqual(ref.source, "mock_ncrp_connector")

    def test_ncrp_fetch_unknown_format_returns_none(self):
        self.assertIsNone(self.ncrp.fetch_complaint("not-a-real-id"))

    def test_ncrp_push_update_succeeds_in_mock(self):
        self.assertTrue(self.ncrp.push_case_update("NCRP-12345", "in_progress", "note"))

    def test_sahyog_lookup_known_entity(self):
        alerts = self.sahyog.lookup_entity_alerts("Krakenish Exchange (mock)")
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].source, "mock_sahyog_connector")

    def test_sahyog_lookup_unknown_entity_returns_empty(self):
        self.assertEqual(self.sahyog.lookup_entity_alerts("Nonexistent Entity"), [])


if __name__ == "__main__":
    unittest.main()
