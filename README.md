# College Savings Calculator

Find the minimum fixed monthly contribution that funds all college bills using your own savings, enrollment timing, costs, and duration. The host chat collects missing essentials and translates the description into typed inputs. The task runs one deterministic Python tool without an inner LLM loop or model-generated monthly schedules. No LLM is used in verification.

## Tools

Task `plan-college-savings` directly calls `calculate_college_savings`; both share `CollegeInput` and `CollegeOutput` in `contract.py`. Money is integer cents in one currency. Rates are integer basis points (100 bps = 1%). Ask for months until enrollment, current savings, annual all-in cost in today's money, and number of college years if missing. Do not guess personal facts.

Every machine-input key is required, including nullable fields: pass null for a default rate or no monthly budget. Zero is an explicit value. Example: a child enrolls in eight years, savings are $15,000, and college currently costs $30,000 a year for four years:

```json
{
  "months_until_enrollment": 96,
  "current_savings_cents": 1500000,
  "annual_college_cost_cents": 3000000,
  "college_years": 4,
  "investment_return_bps": null,
  "cost_inflation_bps": null,
  "monthly_budget_cents": 100000
}
```

## Financial rules

- Default nominal annual investment return: 500 bps (5%). Default annual college-cost inflation: 400 bps (4%). Both can be overridden. Effective inputs and defaulted rate names are returned.
- Use integer months from today. Enrollment N months away permits exactly N deposits, at the ends of months 1 through N. Contributions stop after the last deposit immediately before the first college bill. Enrollment today means no deposits and an immediate bill at month 0.
- Each month first apply investment growth to the opening balance (annual nominal rate divided by 12), then deposit if still in the saving window, then pay any annual bill. Each growth amount is rounded separately to cents, nearest with ties away from zero. New deposits first earn returns the following month.
- College costs inflate at each 12-month anniversary from today, with each annual increase rounded separately to cents. There is no fractional-year cost inflation. At enrollment N, the first bill has floor(N/12) annual inflation increases; further bills occur at N+12, N+24, etc. At an anniversary, cost inflation occurs before that month's bill.
- Savings continue earning returns during college. Annual bills are paid at the beginning of each academic year. Projection ends immediately after the last annual bill, not at the end of the final academic year. A negative balance at any bill means failure; later gains cannot repair a missed bill.
- Search the true minimum whole-cent monthly contribution independently of an optional monthly budget. The budget does not cap the search. Report whether the minimum fits and how much it exceeds the budget. Without a budget those fields remain null.
- If enrollment is immediate and current savings cannot cover every bill, the minimum monthly contribution is null, status is upfront_funding_gap, and the result gives the minimum additional savings needed today to fund every bill. Its first shortfall can be month 0 or a later academic year. Budget fit is false when a budget was supplied; no monthly shortfall amount is fabricated.
- Zero contributions are valid when current savings already fund all bills. Projected enrollment savings are measured before the first bill; total cost is the sum of all future bills, not a present value. A successful result includes the remaining balance after the last bill. That balance is null for an upfront funding gap; adding the stated upfront gap would fund all bills.

Input bounds: months until enrollment 0–360, college years 1–10, monetary inputs 0–10^15 cents, nominal annual investment return −10000 to 10000 bps, cost inflation 0–10000 bps. These bounds keep projections and independent verification finite (at most 468 months). Optional budget is either null or a monetary input. Rate defaults are modeling assumptions, not forecasts or guarantees.

Out of scope: scholarships, loans, taxes, contribution limits or incentives, fees beyond the supplied return, investment volatility, currency conversion, and deposits during college. Include every desired expense in the annual cost input.

## Verification

The calculator uses integer arithmetic and bounded binary search. The verifier separately validates inputs and replays the proposed contribution using Decimal arithmetic. It requires every bill to be funded and, for a positive contribution, requires one cent less per month to fail. This proves minimality because balances are monotone in the contribution under the supported rates and rounding rules. Immediate-enrollment upfront gaps receive the analogous one-cent certificate on additional initial savings. The verifier also checks all summaries, assumptions, defaults, and budget results exactly; no calculator imports, model calls, or workspace files are trusted. It does not verify whether chat correctly interpreted an ambiguous description.

## Layout

`contract.py` holds the typed task/tool. `nanoagent.yaml` selects runner: tool. `src/plugin/` contains the calculator and MCP server. `verifier/` contains independent replay and comparison. `tests/` contains examples, hand-calculated financial boundaries, minimality and budget regressions, randomized replay, and real typed/MCP integration. `product/` and `ui/` supply catalog metadata and the standard host output view.

## Develop and run

Use Python 3.12+:

```bash
python3 tests/validate.py
uv sync --frozen --extra dev
uv run python tests/validate.py --require-runtime
uv run ruff check .
# With NanoAgent installed:
nanoagent plugin inspect .
```

The dependency-free run skips runtime integration if dependencies are absent. `--require-runtime` fails if any test is skipped. Try the editable custom example directly:

```bash
PYTHONPATH=src python3 -c 'import json; from plugin.calculations import solve; print(json.dumps(solve(json.load(open("tests/example.json"))), indent=2))'
```

After installation, the MCP server starts with `NANOAGENT_WORKSPACE=/tmp uv run --frozen python -m plugin`. It requests no network or filesystem write permissions. Invalid inputs receive clear MCP errors. Layout follows arxiv-source at commit 30b5534 and NanoAgent v0001; the required slimconfig master source is pinned to a resolved commit in uv.lock.

Version 0.2.0 replaces the scenario-ID API, scholarship fixtures, and full monthly schedules. Collect actual inputs, live logs, and verdict evidence outside this repository for the assignment PDF. Local validation is not a claim of marketplace publication or a successful live chat run.
