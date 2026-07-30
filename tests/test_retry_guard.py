import tempfile
import unittest

from token_saver.retry_guard import RetryGuard


class RetryGuardTests(unittest.TestCase):
    def test_stops_repeated_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = RetryGuard(directory)
            self.assertTrue(guard.check("pytest", "Assertion failed", max_retries=2)["allowed"])
            self.assertTrue(guard.check("pytest", "Assertion failed", max_retries=2)["allowed"])
            self.assertFalse(guard.check("pytest", "Assertion failed", max_retries=2)["allowed"])


if __name__ == "__main__":
    unittest.main()
