"""Run checks; --require-runtime prevents skipped integration checks from looking complete."""
import argparse
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / 'src')]
parser = argparse.ArgumentParser()
parser.add_argument('--require-runtime', action='store_true', help='Fail if any integration test is skipped')
args = parser.parse_args()
suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
if args.require_runtime and result.skipped:
    print('Incomplete validation: install runtime dependencies and rerun; integration checks were skipped.', file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(0 if result.wasSuccessful() else 1)
