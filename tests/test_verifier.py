import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
import verifier
from plugin.calculations import solve


def example():
    return json.loads((ROOT / "tests/example.json").read_text())


class VerifierTests(unittest.TestCase):
    def judge(self, args, out):
        return verifier.verify_task(verifier.TASK_NAME, args, out, {"untrusted": True}, ROOT)["valid"]

    def test_accepts_custom_input_and_rejects_unknown_dispatch(self):
        args = example()
        out = solve(args)
        self.assertTrue(self.judge(args, out))
        self.assertTrue(verifier.verify_output(verifier.TOOL_NAME, args, out, ROOT)["valid"])
        self.assertFalse(verifier.verify_input("unknown", args)["valid"])
        self.assertFalse(verifier.verify_task("unknown", args, out, None, ROOT)["valid"])

    def test_rejects_changed_value_at_every_output_leaf(self):
        args = example()
        answer = solve(args)

        def leaves(value, path=()):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield from leaves(item, path + (key,))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    yield from leaves(item, path + (index,))
            else:
                yield path, value

        for path, value in leaves(answer):
            invalid = (
                [not value]
                if type(value) is bool
                else [value + 1, float(value), True]
                if type(value) is int
                else ["wrong"]
            )
            for replacement in invalid:
                changed = copy.deepcopy(answer)
                parent = changed
                for slot in path[:-1]:
                    parent = parent[slot]
                parent[path[-1]] = replacement
                with self.subTest(path=path, replacement=replacement):
                    self.assertFalse(self.judge(args, changed))

    def test_missing_malformed_and_extra_output(self):
        args = example()
        out = solve(args)
        for bad in (None, {}, [], "", out | {"schedule": []}):
            self.assertFalse(self.judge(args, bad))
        for key in out:
            bad = dict(out)
            del bad[key]
            self.assertFalse(self.judge(args, bad))

    def test_invalid_inputs_fail_gracefully(self):
        args = example()
        answer = solve(args)
        bad_inputs = [None, {}, [], args | {"scenario_id": "old-api"}]
        for key in args:
            missing = dict(args)
            del missing[key]
            bad_inputs.append(missing)
            bad_inputs.extend(args | {key: invalid} for invalid in (True, 1.0, "1", [], {}, -10001, 10**16))
        for key in ("months_until_enrollment", "current_savings_cents", "annual_college_cost_cents", "college_years"):
            bad_inputs.append(args | {key: None})
        bad_inputs.extend(
            (args | {"months_until_enrollment": 361}, args | {"college_years": 0}, args | {"college_years": 11})
        )
        for bad in bad_inputs:
            with self.subTest(input=bad):
                self.assertFalse(verifier.verify_input(verifier.TOOL_NAME, bad)["valid"])
                self.assertFalse(self.judge(bad, answer))
                with self.assertRaises(ValueError):
                    solve(bad)

    def test_verifier_has_no_dependency_on_calculator(self):
        program = """
import json, sys
sys.path.insert(0, sys.argv[1])
class Block:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'plugin' or fullname.startswith('plugin.'):
            raise AssertionError('verifier must not import calculator')
sys.meta_path.insert(0, Block())
import verifier
args, output = json.load(sys.stdin)
assert verifier.verify_task(verifier.TASK_NAME, args, output, None, '.') ['valid']
assert not verifier.verify_task(verifier.TASK_NAME, args, {}, None, '.') ['valid']
"""
        args = example()
        done = subprocess.run(
            [sys.executable, "-B", "-I", "-c", program, str(ROOT)],
            input=json.dumps([args, solve(args)]),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
