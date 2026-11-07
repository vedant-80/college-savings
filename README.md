# College Savings Contribution Planner

Find the smallest fixed monthly contribution, in cents and within a supplied cap, that pays a college expense schedule on time. Account for existing savings, fixed monthly growth, annual tuition/housing increases, and dated scholarships.

Task ID: `plan-college-savings`. Runner: `agent`. Each monetary value is an integer number of cents; a basis point is 1/100 of a percentage point. No tool solves the task or calls an LLM. All scenarios are synthetic, bundled JSON fixtures, not live financial data.

## Task input and output

Example task input:

```json
{
  "scenario_id": "five-year-start"
}
```

The complete typed output is `CollegeOutput` in `contract.py`; nested row types also live there. All fields and rows are required. Month/year indices start at 1. Only the scenario IDs listed below are accepted. Arbitrary financial inputs are deliberately outside this task's scope.

For a feasible result, return the minimum allowed contribution and every monthly row through the final academic year. If no contribution up to the cap works, submit the cap and its projection through the first negative closing balance. first_shortfall_month=0 means no failure.

## Tools

| Tool | Input | Output |
|---|---|---|
| `get_college_costs` | scenario_id | Enrollment month, program length, annual tuition and housing, and annual cost increase. |
| `get_savings_account` | scenario_id | Initial savings, fixed monthly return in basis points, and allowed monthly contribution cap. |
| `get_scholarships` | scenario_id | All award amounts and disbursement months. |
| `get_rules` | none | Contribution timing, expense timing, growth, rounding, horizon, and infeasibility rules. |

## Exact financial rules

1. Money is integer cents. Months are 1-based. monthly_return_bps is a fixed MONTHLY return, not an annual rate.
2. Year 1 costs are annual_tuition_cents plus annual_housing_cents. Each subsequent academic year multiplies each prior component by 1 + annual_cost_increase_bps/10000, rounding each component to cents, ties up.
3. Pay each academic year costs in full at enrollment_month + 12 * academic_year_index. Horizon ends at enrollment_month + 12 * program_years - 1.
4. Each month: apply growth to opening savings (round to cents, ties up), add the fixed monthly contribution if month < enrollment_month, add scholarships, then pay expenses.
5. Find the smallest nonnegative whole-cent monthly contribution at or below max_monthly_contribution_cents that never makes savings negative.
6. If no allowed contribution works, feasible=false and monthly_contribution_cents must equal the cap. Return its projection through its first shortfall.
7. If feasible, return the full projection through the horizon with first_shortfall_month=0. A failed projection stops at the first negative closing balance. No borrowing or taxes are modeled.

## Bundled scenarios

- `five-year-start`
- `already-funded`
- `zero-growth`
- `immediate-shortfall`
- `scholarship-funded`
- `cap-insufficient`
- `late-scholarship`

Data: `src/plugin/data/scenarios.json`; authoritative rule text: `src/plugin/data/rules.json`. Scenario IDs are dictionary keys, never paths. Tools reread packaged fixtures and do not mutate data or use the workspace. Permission declarations request no network hosts or filesystem writes.

## Reproduce locally

Use Python 3.12 or later. From this plugin's directory:

```bash
# Financial calculations, fixture tools, malformed-output tests, and boundary tests:
python3 tests/validate.py

# Sample candidate output plus the independent verifier verdict; no dependencies needed:
python3 tests/solve.py five-year-start > /tmp/college-savings-example.json

# Full typed-contract and MCP integration, after installing uv:
uv sync --frozen --extra dev
uv run python tests/validate.py --require-runtime
uv run ruff check .
```

The standard-library test command explicitly skips the integration tests if runtime dependencies are missing. `--require-runtime` fails if any tests are skipped, so a partial run cannot count as complete runtime validation. Integration tests round-trip real slimconfig contracts, call every MCP handler, and launch the actual stdio server with an MCP client.

`uv.lock` inherits the resolved dependency graph and package hashes from the supplied arxiv-source reference, with this project's identity updated and slimconfig pinned to that reference's exact commit. Runtime dependency installation requires network access once; the task itself runs offline afterward. The frozen lock still needs a successful uv sync on a network-enabled machine to confirm installation.

To start the server directly after installation:

```bash
NANOAGENT_WORKSPACE=/tmp uv run --frozen python -m plugin
```

The server communicates via MCP stdio; it is normally launched by NanoAgent, not used as an interactive terminal program. `tests/solve.py` is an offline example candidate generator, excluded from the MCP tool list; it is not an agent evaluation run.

## Verifier

The verifier independently replays the submitted contribution with Decimal arithmetic and compares every row and summary. For a positive feasible contribution it also replays one cent less and requires failure. With the bundled nonnegative returns, larger contributions cannot reduce balances, so this certifies global minimality. An infeasibility claim is accepted only when the cap fails. The sample solver uses integer arithmetic and binary search.

The verifier accepts either contract dataclass instances (the harness interface) or raw dictionaries (local checks). Public entry points follow the reference: `verify_input(tool, value)`, `verify_output(tool, input_value, output_value, workspace)`, and `verify_task(task, arguments, output, reference, workspace)`. Verdicts contain `valid`, `score`, `message`, and `details`. The task check ignores any supplied reference answer and recomputes from trusted literals in `verifier/fixtures.py`. Tests ensure those literals match the packaged JSON. The verifier imports no MCP implementation code and reads no agent-controlled fixture files.

Checks reject missing/extra fields, changed values, truncated or duplicated rows, incorrect ordering, booleans/floats substituted for integer cents, unknown scenarios, and invalid input bounds. Tool verifiers compare retrieved data to fixtures; task verifiers use independent financial implementations. Tests include hand-calculated cases, all bundled scenarios, negative-output mutations, and 100 deterministically seeded scenario variations per plugin.

## Layout and reference

```text
contract.py             Typed task/tool schemas and registries
nanoagent.yaml          NanoAgent runtime, permissions, tools, and agent task
pyproject.toml, uv.lock Standalone package metadata and pinned dependencies
src/plugin/            MCP server, read-only tools, bundled data, offline sample calculations
verifier/              Semantic validation and independent financial replay
tests/                 Verifier tests, validation/example CLIs, and optional runtime integration
product/, ui/          Catalog metadata, icon, and default host-renderer declaration
```

Layout and MCP integration follow [arxiv-source at commit 30b5534](https://github.com/zeyuyang8/arxiv-source/tree/30b5534a8ed17f53c3e87d7a092ae20b1e5f6d24). The financial tasks, tools, data, and checks are original implementations. This directory is standalone and does not import either sibling finance plugin or the reference checkout.

## Limitations and submission evidence

Fixed nonnegative monthly return assumptions; no market uncertainty, taxes, 529-specific rules, loans, contribution changes, or financial-aid eligibility calculations. Expenses are paid annually at the start of each academic year. Contributions stop at enrollment. The cap is part of the task, so infeasible means infeasible within that cap.

These scenarios demonstrate calculations under stated assumptions and are not personalized financial advice. No RUSH Lab publication or live agent run is claimed. Collect actual task inputs, validation logs, and verifier verdicts outside this repository for the assignment PDF; the example command above writes to `/tmp` for that reason. A passing sample solver run demonstrates the verifier path, not that an agent successfully completed the task.
