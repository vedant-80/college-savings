"""Independent Decimal replay and one-cent minimality certificates. No calculator imports."""

from dataclasses import asdict, is_dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    return value


def normalize(value):
    args = asdict(value) if is_dataclass(value) else value
    fields = {
        "months_until_enrollment",
        "current_savings_cents",
        "annual_college_cost_cents",
        "college_years",
        "investment_return_bps",
        "cost_inflation_bps",
        "monthly_budget_cents",
    }
    if type(args) is not dict or set(args) != fields:
        raise ValueError("Supply all declared fields; use null for optional assumptions or no budget")
    a = {}
    for key, low, high in (
        ("months_until_enrollment", 0, 360),
        ("current_savings_cents", 0, 10**15),
        ("annual_college_cost_cents", 0, 10**15),
        ("college_years", 1, 10),
    ):
        a[key] = integer(args[key], key, low, high)
    defaults = []
    for key, default, low in (("investment_return_bps", 500, -10000), ("cost_inflation_bps", 400, 0)):
        value = args[key]
        if value is None:
            value = default
            defaults.append(key)
        a[key] = integer(value, key, low, 10000)
    budget = args["monthly_budget_cents"]
    a["monthly_budget_cents"] = None if budget is None else integer(budget, "monthly_budget_cents", 0, 10**15)
    return a, defaults


def round_cent(amount):
    return int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def expense_table(a):
    table = {}
    for year in range(a["college_years"]):
        when = a["months_until_enrollment"] + year * 12
        cost = a["annual_college_cost_cents"]
        for _ in range(when // 12):
            cost += round_cent(Decimal(cost) * a["cost_inflation_bps"] / 10000)
        table[when] = cost
    return table


def simulate(a, table, monthly, upfront=0):
    assets = a["current_savings_cents"] + upfront
    enrollment = a["months_until_enrollment"]
    at_enrollment = None
    for elapsed in range(max(table) + 1):
        if elapsed > 0:
            assets += round_cent(Decimal(assets) * a["investment_return_bps"] / 120000)
            if elapsed <= enrollment:
                assets += monthly
        if elapsed == enrollment:
            at_enrollment = assets
        if elapsed in table:
            assets -= table[elapsed]
        if assets < 0:
            return False, elapsed, at_enrollment, None
    return True, None, at_enrollment, assets


def check_result(value, output):
    a, defaults = normalize(value)
    if type(output) is not dict:
        raise ValueError("Expected a result object")
    with localcontext() as context:
        # Bounds: <=468 months, annual input inflation <=100%, investment monthly factor >=11/12.
        # Even a 2**256 certificate grows to fewer than 100 decimal digits over this horizon.
        context.prec = 200
        table = expense_table(a)
        contribution = output["minimum_monthly_contribution_cents"]
        if contribution is None:
            if a["months_until_enrollment"] != 0:
                raise ValueError("A positive saving window permits a monthly contribution plan")
            funded, failure, at_enrollment, ending = simulate(a, table, 0)
            if funded:
                raise ValueError("Already funded; minimum contribution is zero")
            additional = integer(output["additional_savings_needed_now_cents"], "additional savings", 1, 2**256)
            if not simulate(a, table, 0, additional)[0] or simulate(a, table, 0, additional - 1)[0]:
                raise ValueError("Upfront amount is insufficient or not minimal")
        else:
            integer(contribution, "monthly contribution", 0, 2**256)
            funded, failure, at_enrollment, ending = simulate(a, table, contribution)
            if not funded:
                raise ValueError("Contribution does not fund every annual payment")
            if contribution and simulate(a, table, contribution - 1)[0]:
                raise ValueError("Contribution is sufficient but not minimal")
            additional = 0
        possible = contribution is not None
        budget = a["monthly_budget_cents"]
        return {
            "monthly_plan_possible": possible,
            "reason": "funded" if possible else "upfront_funding_gap",
            "minimum_monthly_contribution_cents": contribution,
            "projected_savings_at_enrollment_cents": at_enrollment,
            "projected_total_college_cost_cents": sum(table.values()),
            "projected_balance_after_final_payment_cents": ending,
            "additional_savings_needed_now_cents": additional,
            "first_shortfall_month": failure,
            "fits_monthly_budget": None if budget is None else possible and contribution <= budget,
            "monthly_budget_shortfall_cents": None if budget is None or not possible else max(0, contribution - budget),
            "assumptions": a,
            "defaults_applied": defaults,
        }
