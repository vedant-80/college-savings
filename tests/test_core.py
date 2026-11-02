"""Financial and verifier tests run without installing the MCP transport dependencies."""
import ast
import copy
from pathlib import Path
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from plugin.data import scenarios
from plugin.calculations import solve
from plugin.tools import IMPLEMENTATIONS
import verifier

TASK = 'plan-college-savings'
OUTPUT_CLASS = 'CollegeOutput'

def arguments(identifier):
    result = {'scenario_id': identifier}
    if TASK == 'project-retirement':
        result['years'] = 30
    return result

class FinancialVerifierTests(unittest.TestCase):
    def judge(self, args, output):
        return verifier.verify_task(TASK, args, output, {'untrusted': 'not an answer key'}, str(ROOT))['valid']

    def test_accepts_every_bundled_scenario(self):
        for identifier in scenarios():
            with self.subTest(scenario=identifier):
                args = arguments(identifier)
                self.assertTrue(self.judge(args, solve(args)))

    def test_rejects_wrong_summary_values(self):
        for identifier in scenarios():
            args = arguments(identifier)
            answer = solve(args)
            for key, value in answer.items():
                if key == 'schedule' or key == 'baseline_schedule':
                    continue
                bad = copy.deepcopy(answer)
                bad[key] = not value if type(value) is bool else value + 1 if type(value) is int else 'wrong'
                with self.subTest(scenario=identifier, field=key):
                    self.assertFalse(self.judge(args, bad))

    def test_rejects_every_changed_first_row_field(self):
        for identifier in scenarios():
            args = arguments(identifier)
            answer = solve(args)
            for key, value in answer['schedule'][0].items():
                bad = copy.deepcopy(answer)
                bad['schedule'][0][key] = value + 1 if type(value) is int else 'wrong'
                with self.subTest(scenario=identifier, field=key):
                    self.assertFalse(self.judge(args, bad))

    def test_rejects_missing_malformed_and_extra_output(self):
        args = arguments(next(iter(scenarios())))
        answer = solve(args)
        for bad in (None, {}, [], '', answer | {'unexpected': 1}):
            self.assertFalse(self.judge(args, bad))
        for field in answer:
            bad = copy.deepcopy(answer)
            del bad[field]
            self.assertFalse(self.judge(args, bad))

    def test_rejects_missing_duplicate_and_reordered_schedule_rows(self):
        args = arguments(next(iter(scenarios())))
        answer = solve(args)
        for rows in ([], answer['schedule'][:-1], answer['schedule'] + answer['schedule'][-1:], list(reversed(answer['schedule']))):
            self.assertFalse(self.judge(args, answer | {'schedule': rows}))

    def test_rejects_float_and_boolean_money(self):
        args = arguments(next(iter(scenarios())))
        answer = solve(args)
        key = next(k for k,v in answer['schedule'][0].items() if type(v) is int)
        for invalid in (float(answer['schedule'][0][key]), True, '1', None):
            bad = copy.deepcopy(answer)
            bad['schedule'][0][key] = invalid
            self.assertFalse(self.judge(args, bad))

    def test_rejects_unknown_task_scenario_and_malformed_inputs(self):
        answer = solve(arguments(next(iter(scenarios()))))
        invalid = [None, {}, [], {'scenario_id': '../secrets'}, {'scenario_id': True}]
        if TASK == 'project-retirement':
            invalid.extend({'scenario_id': 'comfortable', 'years': y} for y in (0, 61, True, 1.0, '30'))
        for args in invalid:
            self.assertFalse(self.judge(args, answer))
        self.assertFalse(verifier.verify_task('unknown', arguments(next(iter(scenarios()))), answer, None, '.')['valid'])

    def test_tools_return_exact_fixture_data_and_reject_fabrication(self):
        for identifier, item in scenarios().items():
            for name, function in IMPLEMENTATIONS.items():
                args = {} if name == 'get_rules' else {'scenario_id': identifier}
                if name == 'get_extra_payments':
                    args |= {'start_month': 1, 'end_month': item['loan']['term_months']}
                with self.subTest(scenario=identifier, tool=name):
                    self.assertTrue(verifier.verify_input(name, args)['valid'])
                    out = function(args, ROOT)
                    self.assertTrue(verifier.verify_output(name, args, out, ROOT)['valid'])
                    self.assertFalse(verifier.verify_output(name, args, out | {'fabricated': 1}, ROOT)['valid'])
                    for missing in (None, {}, []):
                        self.assertFalse(verifier.verify_output(name, args, missing, ROOT)['valid'])

    def test_tools_reject_bad_inputs(self):
        for name in IMPLEMENTATIONS:
            for args in (None, [], {'scenario_id': '../arbitrary-file'}, {'unknown': 1}):
                self.assertFalse(verifier.verify_input(name, args)['valid'])
        self.assertFalse(verifier.verify_input('unknown', {})['valid'])

    def test_tools_do_not_mutate_fixture_state(self):
        name = next(n for n in IMPLEMENTATIONS if n not in ('get_rules', 'get_extra_payments'))
        args = {'scenario_id': next(iter(scenarios()))}
        first = IMPLEMENTATIONS[name](args, ROOT)
        pristine = copy.deepcopy(first)
        first.clear()
        self.assertEqual(IMPLEMENTATIONS[name](args, ROOT), pristine)

    def test_declared_output_shape_matches_every_scenario(self):
        # Static contract checks remain executable when slimconfig is unavailable.
        tree = ast.parse((ROOT / 'contract.py').read_text())
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
        def check(annotation, value):
            if isinstance(annotation, ast.Subscript):
                self.assertIs(type(value), list)
                for child in value:
                    check(annotation.slice, child)
            elif annotation.id in ('int', 'str', 'bool'):
                self.assertIs(type(value), {'int': int, 'str': str, 'bool': bool}[annotation.id])
            else:
                fields = {n.target.id: n.annotation for n in classes[annotation.id].body if isinstance(n, ast.AnnAssign)}
                self.assertEqual(set(value), set(fields))
                for key, field in fields.items():
                    check(field, value[key])
        for identifier in scenarios():
            check(ast.Name(id=OUTPUT_CLASS), solve(arguments(identifier)))

    def test_packaging_and_lockfile_match(self):
        metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text())
        lock = tomllib.loads((ROOT / 'uv.lock').read_text())
        package = next(p for p in lock['package'] if p['name'] == metadata['project']['name'])
        self.assertEqual(package['version'], metadata['project']['version'])
        self.assertEqual(package['source'], {'editable': '.'})
        self.assertEqual(metadata['tool']['setuptools']['package-data']['plugin'], ['data/*.json'])

if __name__ == '__main__':
    unittest.main()
