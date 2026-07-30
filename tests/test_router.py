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
        self.assertEqual(result.model, "gpt-5.6-sol")
        self.assertEqual(result.reasoning_effort, "high")

    def test_routine_routes_terra_medium(self):
        result = recommend_tier("Implement the documented parser change and run its tests.")
        self.assertEqual((result.model, result.reasoning_effort), ("gpt-5.6-terra", "medium"))

    def test_risk_floor_overrides_deterministic_keyword(self):
        result = recommend_tier("Replace the production credential validation policy.")
        self.assertEqual(result.tier, "powerful")
        self.assertTrue(result.advisory)

    def test_architecture_routes_sol_even_in_one_file(self):
        result = recommend_tier("Design the migration architecture.", file_count=1)
        self.assertEqual((result.model, result.reasoning_effort), ("gpt-5.6-sol", "high"))


if __name__ == "__main__":
    unittest.main()
