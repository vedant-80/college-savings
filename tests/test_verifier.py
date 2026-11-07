"""Admission regressions and isolation of the trusted verifier from MCP code."""
import ast
from dataclasses import make_dataclass
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class AdmissionTests(unittest.TestCase):
    def test_reported_packaging_requirements(self):
        self.assertFalse((ROOT / 'scripts').exists())
        self.assertIn('*.pyc', (ROOT / '.gitignore').read_text().splitlines())
        for source in (ROOT / 'verifier').rglob('*.py'):
            for node in ast.walk(ast.parse(source.read_text())):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    modules = [node.module or '']
                else:
                    continue
                for module in modules:
                    with self.subTest(source=source.name, module=module):
                        self.assertNotIn(module.split('.')[0], ('types', 'plugin'))

    def test_verifier_runs_without_plugin_package(self):
        program = '''
import sys
sys.path.insert(0, sys.argv[1])
class BlockPlugin:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'plugin' or fullname.startswith('plugin.'):
            raise AssertionError('verifier must not import plugin')
sys.meta_path.insert(0, BlockPlugin())
import json
import verifier
from verifier.fixtures import scenarios, tool_output
for identifier in scenarios():
    for name in verifier.TOOLS:
        args = {} if name == 'get_rules' else {'scenario_id': identifier}
        if name == 'get_extra_payments':
            args.update(start_month=1, end_month=1)
        output = tool_output(name, args)
        assert verifier.TOOLS[name].verify_input(args)['valid']
        assert verifier.TOOLS[name].verify_output(args, output, '.')['valid']
for args, output in json.loads(sys.stdin.read()):
    assert verifier.verify_task(verifier.TASK_NAME, args, output, None, '.')['valid']
    assert not verifier.verify_task(verifier.TASK_NAME, args, {}, None, '.')['valid']
'''
        sys.path.insert(0, str(ROOT / 'src'))
        from plugin.calculations import solve
        from verifier.fixtures import scenarios
        import verifier
        cases = []
        for identifier in scenarios():
            args = {'scenario_id': identifier}
            if verifier.TASK_NAME == 'project-retirement':
                args['years'] = 30
            cases.append((args, solve(args)))
        completed = subprocess.run([sys.executable, '-I', '-c', program, str(ROOT)],
                                   input=json.dumps(cases), capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_trusted_fixtures_match_packaged_data_and_are_fresh(self):
        from verifier.fixtures import scenarios, rules
        data = ROOT / 'src/plugin/data'
        self.assertEqual(scenarios(), json.loads((data / 'scenarios.json').read_text()))
        self.assertEqual(rules(), json.loads((data / 'rules.json').read_text()))
        changed = scenarios()
        changed.clear()
        self.assertTrue(scenarios())

    def test_accepts_dataclass_tool_inputs_and_nested_outputs(self):
        import verifier
        from verifier.fixtures import scenarios, tool_output

        def typed(value):
            if isinstance(value, dict):
                cls = make_dataclass('Payload', [(key, object) for key in value])
                return cls(**{key: typed(child) for key, child in value.items()})
            if isinstance(value, list):
                return [typed(child) for child in value]
            return value

        identifier = next(iter(scenarios()))
        for name, check in verifier.TOOLS.items():
            args = {} if name == 'get_rules' else {'scenario_id': identifier}
            if name == 'get_extra_payments':
                args.update(start_month=1, end_month=1)
            with self.subTest(tool=name):
                self.assertTrue(check.verify_input(typed(args))['valid'])
                self.assertTrue(check.verify_output(typed(args), typed(tool_output(name, args)), ROOT)['valid'])


if __name__ == '__main__':
    unittest.main()
