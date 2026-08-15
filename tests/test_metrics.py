import unittest

from token_saver.metrics import request_report_text


class RequestReportTextTests(unittest.TestCase):
    def test_formats_all_required_fields_and_material_warnings(self):
        report = {
            "request_id": "request-1",
            "statuses": {"ok": 2},
            "warnings": ["protected content retained"],
            "retrieval": {
                "runs": 1,
                "files_scanned": 12,
                "passages_returned": 6,
                "files_skipped_ignored": 2,
                "files_skipped_sensitive": 1,
                "files_skipped_symlink": 0,
                "limit_reached": False,
            },
            "compaction": {
                "runs": 1,
                "estimated_tokens_before": 100,
                "estimated_tokens_after": 60,
                "estimated_tokens_avoided": 40,
                "estimated_savings_percent": 40.0,
            },
            "provider_usage_available": True,
            "provider_usage_totals": {"input_tokens": 150, "cost_usd": 0.01},
        }

        text = request_report_text(report)

        self.assertTrue(text.startswith("Token Saver request report\n"))
        self.assertIn("- run: `request-1`", text)
        self.assertIn("12 files scanned; 6 passages", text)
        self.assertIn("100 -> 60 estimated tokens; avoided 40 (40.0%)", text)
        self.assertIn("ok (2); warnings: protected content retained", text)
        self.assertIn("cost_usd=0.01, input_tokens=150", text)
