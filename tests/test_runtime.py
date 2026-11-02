"""Real contract and MCP integration; skipped only when dependencies are not installed."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
AVAILABLE = all(importlib.util.find_spec(n) is not None for n in ('slimconfig', 'mcp', 'anyio'))

@unittest.skipUnless(AVAILABLE, 'Install runtime dependencies with uv sync --frozen --extra dev')
class RuntimeIntegrationTests(unittest.TestCase):
    def test_real_slimconfig_round_trip_and_verifier(self):
        from contract import TASKS, Task
        from slimconfig import build_output, output_schema, plain_output
        from plugin.calculations import solve
        from plugin.data import scenarios
        import verifier
        task = next(iter(Task))
        given, made = TASKS[task]
        for identifier in scenarios():
            args = {'scenario_id': identifier}
            if task.value == 'project-retirement':
                args['years'] = 30
            typed_args = build_output(args, given)
            answer = solve(args)
            typed_result = build_output(answer, made)
            self.assertEqual(plain_output(typed_result), answer)
            self.assertTrue(output_schema(made))
            self.assertTrue(verifier.verify_task(task, typed_args, typed_result, None, ROOT)['valid'])

    def test_mcp_lists_and_executes_all_typed_tools(self):
        from plugin.__main__ import list_tools, call_tool
        from plugin.data import scenarios
        from contract import TOOLS, Tool
        from slimconfig import build_output
        import verifier
        identifier = next(iter(scenarios()))
        os.environ['NANOAGENT_WORKSPACE'] = str(ROOT)
        listed = asyncio.run(list_tools())
        self.assertEqual({tool.name for tool in listed}, {tool.value for tool in Tool})
        for tool, (given, made) in TOOLS.items():
            args = {} if tool.value == 'get_rules' else {'scenario_id': identifier}
            if tool.value == 'get_extra_payments':
                args |= {'start_month': 1, 'end_month': scenarios()[identifier]['loan']['term_months']}
            answer = asyncio.run(call_tool(tool.value, args))
            self.assertTrue(verifier.verify_output(tool, build_output(args, given), build_output(answer, made), ROOT)['valid'])

    def test_real_stdio_transport(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def exercise():
            environment = dict(os.environ)
            environment['NANOAGENT_WORKSPACE'] = str(ROOT)
            environment['PYTHONPATH'] = os.pathsep.join((str(ROOT), str(ROOT / 'src')))
            parameters = StdioServerParameters(command=sys.executable, args=['-m', 'plugin'], env=environment)
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    self.assertIn('get_rules', {tool.name for tool in listed.tools})
                    result = await session.call_tool('get_rules', {})
                    self.assertFalse(result.isError)
                    payload = result.structuredContent
                    if payload is None:
                        import json
                        payload = json.loads(result.content[0].text)
                    self.assertTrue(payload['rules'])
        asyncio.run(asyncio.wait_for(exercise(), timeout=20))
