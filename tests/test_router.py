import unittest

from token_saver.router import recommend_tier


class RouterTests(unittest.TestCase):
    def test_deterministic_routes_economy(self):
        result = recommend_tier("Convert this JSON to YAML and sort the keys.")
        self.assertEqual(result.tier, "economy")

    def test_complex_routes_powerful(self):
        result = recommend_tier(
            "Investigate and redesign the security architecture migration across frontend, backend, API, and database for a production outage.",
            file_count=20,
            high_stakes=True,
        )
        self.assertEqual(result.tier, "powerful")


if __name__ == "__main__":
    unittest.main()
