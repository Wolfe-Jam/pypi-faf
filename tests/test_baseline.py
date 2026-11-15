"""Baseline + new days: the all-time total that never goes down."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
from render import BaselineError, advance  # noqa: E402

TODAY = date(2026, 11, 16)


class Advance(unittest.TestCase):
    def test_adds_only_days_after_through(self):
        base = {"total": 100, "through": "2026-11-14"}
        days = {"2026-11-13": 50, "2026-11-14": 7, "2026-11-15": 3}
        self.assertEqual(advance(base, days, TODAY), {"total": 103, "through": "2026-11-15"})

    def test_same_days_twice_adds_nothing(self):
        base = {"total": 100, "through": "2026-11-14"}
        days = {"2026-11-14": 7, "2026-11-15": 3}
        once = advance(base, days, TODAY)
        self.assertEqual(advance(once, days, TODAY), once)

    def test_old_days_leaving_the_window_never_lower_it(self):
        base = {"total": 100, "through": "2026-11-14"}
        self.assertEqual(advance(base, {"2026-11-15": 2}, TODAY)["total"], 102)

    def test_no_rows_keeps_baseline(self):
        base = {"total": 100, "through": "2026-11-14"}
        self.assertEqual(advance(base, {}, TODAY), base)

    def test_new_package_counts_its_window(self):
        days = {"2026-11-10": 4, "2026-11-15": 1}
        self.assertEqual(advance(None, days, TODAY), {"total": 5, "through": "2026-11-15"})

    def test_new_package_without_rows(self):
        self.assertEqual(advance(None, {}, TODAY), {"total": 0, "through": "2026-11-15"})

    def test_stale_baseline_refuses(self):
        base = {"total": 100, "through": "2026-05-01"}
        with self.assertRaises(BaselineError):
            advance(base, {"2026-11-15": 1}, TODAY)


if __name__ == "__main__":
    unittest.main()
