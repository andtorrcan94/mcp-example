import unittest
from unittest.mock import AsyncMock, patch

from server import normalize_request_id, simulated_result


class ScenarioTests(unittest.IsolatedAsyncioTestCase):
    def test_spoken_fixture_id(self):
        for spoken in ["test o o one", "TEST zero zero one", "test oh oh one", "TEST-001"]:
            self.assertEqual(normalize_request_id(spoken), "TEST-001")
        self.assertEqual(normalize_request_id("another request one"), "another request one")
        self.assertEqual(normalize_request_id("../health"), "../health")

    async def test_status_waits_without_guaranteeing_a_date(self):
        with patch("server.asyncio.sleep", new_callable=AsyncMock) as wait:
            status, result = await simulated_result("TEST-001", "status")
        wait.assert_awaited_once_with(20)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "under_review")
        self.assertIsNone(result["resolution_date"])
        self.assertFalse(result["can_guarantee_resolution_today"])

    async def test_failure_waits_and_does_not_claim_an_action(self):
        with patch("server.asyncio.sleep", new_callable=AsyncMock) as wait:
            status, result = await simulated_result("TEST-001", "failure")
        wait.assert_awaited_once_with(20)
        self.assertEqual(status, 503)
        self.assertIn("No action", result["message"])

    async def test_missing_is_immediate_and_unknown(self):
        with patch("server.asyncio.sleep", new_callable=AsyncMock) as wait:
            status, result = await simulated_result("TEST-MISSING", "missing")
        wait.assert_not_awaited()
        self.assertEqual(status, 200)
        self.assertFalse(result["found"])

    async def test_invalid_id_cannot_be_used_as_a_path(self):
        status, _ = await simulated_result("../health", "status")
        self.assertEqual(status, 400)
