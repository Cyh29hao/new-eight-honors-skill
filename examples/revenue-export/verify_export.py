"""Run isolated export checks using example orders and the standard library."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT


class RevenueExportTests(unittest.TestCase):
    def assert_export(self, orders, expected):
        with tempfile.TemporaryDirectory(prefix='export-check-', dir=ROOT) as directory:
            sandbox = Path(directory)
            (sandbox / 'orders.json').write_text(json.dumps(orders), encoding='utf-8')
            subprocess.run(
                [sys.executable, '-B', str(PROJECT / 'export_report.py')],
                cwd=sandbox,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                (sandbox / 'summary.txt').read_text(encoding='utf-8'), expected
            )

    def test_provided_example(self):
        orders = json.loads((PROJECT / 'orders.json').read_text(encoding='utf-8'))
        self.assert_export(orders, 'Completed revenue: 20.00\n')

    def test_mixed_statuses(self):
        self.assert_export([
            {'status': 'completed', 'amount': '19.90'},
            {'status': 'cancelled', 'amount': '100.00'},
            {'status': 'pending', 'amount': '50.00'},
            {'status': 'refunded', 'amount': '8.00'},
            {'status': 'completed', 'amount': '0.10'},
        ], 'Completed revenue: 20.00\n')

    def test_no_completed_orders(self):
        self.assert_export([
            {'status': 'cancelled', 'amount': '100.00'},
            {'status': 'pending', 'amount': '50.00'},
        ], 'Completed revenue: 0.00\n')

    def test_empty_orders(self):
        self.assert_export([], 'Completed revenue: 0.00\n')

    def test_decimal_amounts(self):
        self.assert_export([
            {'status': 'completed', 'amount': '0.10'},
            {'status': 'completed', 'amount': '0.20'},
        ], 'Completed revenue: 0.30\n')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RevenueExportTests)
    with (ROOT / 'verification.txt').open('w', encoding='utf-8', newline='\n') as evidence:
        result = unittest.TextTestRunner(stream=evidence, verbosity=2).run(suite)
    sys.stdout.write((ROOT / 'verification.txt').read_text(encoding='utf-8'))
    raise SystemExit(0 if result.wasSuccessful() else 1)
