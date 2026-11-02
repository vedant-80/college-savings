"""Typed MCP stdio entry point, following the arxiv-source reference layout."""
import os
from pathlib import Path
import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from slimconfig import build_output, output_schema, plain_output
from contract import TOOLS, Tool
from plugin.tools import IMPLEMENTATIONS

server = Server('college-savings')

@server.list_tools()
async def list_tools():
    return [types.Tool(name=t.value, description=IMPLEMENTATIONS[t.value].__doc__,
                       inputSchema=output_schema(i), outputSchema=output_schema(o))
            for t, (i, o) in TOOLS.items()]

@server.call_tool()
async def call_tool(name, arguments):
    tool = Tool(name)
    given, made = TOOLS[tool]
    value = build_output(arguments, given)
    result = IMPLEMENTATIONS[name](value, Path(os.environ['NANOAGENT_WORKSPACE']))
    return plain_output(build_output(result, made))

def main():
    if 'NANOAGENT_WORKSPACE' not in os.environ:
        raise SystemExit('NANOAGENT_WORKSPACE must be supplied by NanoAgent')
    if set(IMPLEMENTATIONS) != {t.value for t in Tool}:
        raise SystemExit('Every contract tool must have an implementation')
    async def run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    anyio.run(run)

if __name__ == '__main__':
    main()
