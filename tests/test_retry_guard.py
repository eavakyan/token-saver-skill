import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from token_saver.retry_guard import RetryGuard


class RetryGuardTests(unittest.TestCase):
    def test_stops_repeated_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = RetryGuard(directory)
            self.assertTrue(guard.check("pytest", "Assertion failed", max_retries=2)["allowed"])
            self.assertTrue(guard.check("pytest", "Assertion failed", max_retries=2)["allowed"])
            self.assertFalse(guard.check("pytest", "Assertion failed", max_retries=2)["allowed"])

    def test_concurrent_checks_are_not_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = RetryGuard(directory, scope="branch-a")
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: guard.check("pytest", "same failure", max_retries=100), range(24)))
            self.assertEqual(sorted(result["attempt"] for result in results), list(range(1, 25)))

    def test_scopes_ttl_and_reset_are_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            first = RetryGuard(directory, scope="one")
            second = RetryGuard(directory, scope="two")
            self.assertEqual(first.check("op", "error")["attempt"], 1)
            self.assertEqual(second.check("op", "error")["attempt"], 1)
            self.assertEqual(first.reset(), 1)
            self.assertEqual(first.check("op", "error")["attempt"], 1)


if __name__ == "__main__":
    unittest.main()
