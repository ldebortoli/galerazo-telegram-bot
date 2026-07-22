import unittest

from scripts.check_coverage import coverage_failures


class CoveragePolicyTests(unittest.TestCase):
    def test_accepts_only_full_coverage(self) -> None:
        self.assertEqual(
            coverage_failures(
                {
                    "percent_statements_covered": 100.0,
                    "percent_branches_covered": 100.0,
                }
            ),
            [],
        )

    def test_reports_each_regressed_metric(self) -> None:
        failures = coverage_failures(
            {
                "percent_statements_covered": 99.99,
                "percent_branches_covered": 99.99,
            }
        )

        self.assertEqual(len(failures), 2)
        self.assertIn("Statement coverage", failures[0])
        self.assertIn("Branch coverage", failures[1])


if __name__ == "__main__":
    unittest.main()
