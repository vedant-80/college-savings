"""Real typed-contract and MCP checks; required for full validation."""

import asyncio
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ("slimconfig", "mcp", "anyio"))


@unittest.skipUnless(AVAILABLE, "Install dependencies with uv sync --frozen --extra dev")
class RuntimeTests(unittest.TestCase):
    def test_real_contract_and_typed_verifier(self):
        from slimconfig import build_output, output_schema, plain_output

        import verifier
        from contract import TASKS, TOOLS, Task, Tool
        from plugin.calculations import solve

        args = json.loads((ROOT / "tests/example.json").read_text())
        for key in args:
            if key in ("investment_return_bps", "cost_inflation_bps", "monthly_budget_cents"):
                args[key] = None
        given, made = TASKS[Task.CALCULATE]
        self.assertEqual(TOOLS[Tool.CALCULATE], (given, made))
        typed = build_output(args, given)
        result = build_output(solve(typed), made)
        self.assertTrue(verifier.verify_task(Task.CALCULATE, typed, result, None, ROOT)["valid"])
        self.assertEqual(plain_output(result), solve(args))
        self.assertTrue(output_schema(given))
        self.assertTrue(output_schema(made))
        missing = dict(args)
        del missing[next(iter(missing))]
        with self.assertRaises((ValueError, TypeError)):
            build_output(missing, given)

    def test_mcp_handler_returns_calculated_result(self):
        from contract import Tool
        from plugin.__main__ import call_tool, list_tools
        from plugin.calculations import solve

        args = json.loads((ROOT / "tests/example.json").read_text())
        os.environ["NANOAGENT_WORKSPACE"] = str(ROOT)
        listed = asyncio.run(list_tools())
        self.assertEqual([tool.name for tool in listed], [Tool.CALCULATE.value])
        self.assertEqual(asyncio.run(call_tool(Tool.CALCULATE.value, args)), solve(args))

    def test_actual_stdio_calculation_and_error(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        from contract import Tool
        from plugin.calculations import solve

        args = json.loads((ROOT / "tests/example.json").read_text())

        async def exercise():
            environment = dict(os.environ)
            environment["NANOAGENT_WORKSPACE"] = str(ROOT)
            environment["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "src")))
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            parameters = StdioServerParameters(command=sys.executable, args=["-B", "-m", "plugin"], env=environment)
            async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                self.assertEqual([tool.name for tool in listed.tools], [Tool.CALCULATE.value])
                result = await session.call_tool(Tool.CALCULATE.value, args)
                self.assertFalse(result.isError)
                payload = result.structuredContent
                if payload is None:
                    payload = json.loads(result.content[0].text)
                self.assertEqual(payload, solve(args))
                bad = args | {"months_until_enrollment": -1}
                invalid = await session.call_tool(Tool.CALCULATE.value, bad)
                self.assertTrue(invalid.isError)

        asyncio.run(asyncio.wait_for(exercise(), timeout=20))
