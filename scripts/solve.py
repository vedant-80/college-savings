"""Offline demonstration only; this solver is not exposed as an agent tool."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugin.calculations import solve
from verifier import verify_task

parser = argparse.ArgumentParser()
parser.add_argument('scenario_id')

args = parser.parse_args()
given = {'scenario_id': args.scenario_id}
output = solve(given)
verdict = verify_task('plan-college-savings', given, output, None, '.')
print(json.dumps({'input': given, 'output': output, 'verdict': verdict}, indent=2))
raise SystemExit(0 if verdict['valid'] else 1)
