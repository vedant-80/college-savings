"""Custom college savings calculation using integer cents and bounded monotone search."""

from dataclasses import asdict, is_dataclass

MAX_SEARCH_AMOUNT = 2**256


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    return value


def rounded(numerator, denominator):
    sign = -1 if numerator < 0 else 1
    return sign * ((2 * abs(numerator) + denominator) // (2 * denominator))


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


def bills(a):
    last = a["months_until_enrollment"] + 12 * (a["college_years"] - 1)
    cost = a["annual_college_cost_cents"]
    due = {}
    for month in range(last + 1):
        if month and month % 12 == 0:
            cost += rounded(cost * a["cost_inflation_bps"], 10000)
        if month >= a["months_until_enrollment"] and (month - a["months_until_enrollment"]) % 12 == 0:
            due[month] = cost
    return due


def replay(a, due, contribution, additional_now=0):
    balance = a["current_savings_cents"] + additional_now
    enrollment_balance = balance if a["months_until_enrollment"] == 0 else None
    for month in range(max(due) + 1):
        if month:
            balance += rounded(balance * a["investment_return_bps"], 120000)
            if month <= a["months_until_enrollment"]:
                balance += contribution
        if month == a["months_until_enrollment"]:
            enrollment_balance = balance
        balance -= due.get(month, 0)
        if balance < 0:
            return {
                "funded": False,
                "first_shortfall_month": month,
                "enrollment_balance": enrollment_balance,
                "final_balance": None,
            }
    return {
        "funded": True,
        "first_shortfall_month": None,
        "enrollment_balance": enrollment_balance,
        "final_balance": balance,
    }


def minimum_amount(succeeds):
    if succeeds(0):
        return 0
    upper = 1
    while not succeeds(upper):
        upper *= 2
        if upper > MAX_SEARCH_AMOUNT:
            raise ValueError("Input exceeds the bounded calculation capacity")
    lower = 0
    while lower < upper:
        middle = (lower + upper) // 2
        if succeeds(middle):
            upper = middle
        else:
            lower = middle + 1
    return lower


def solve(value):
    a, defaults = normalize(value)
    due = bills(a)
    no_saving = replay(a, due, 0)
    if a["months_until_enrollment"] == 0 and not no_saving["funded"]:
        contribution = None
        additional = minimum_amount(lambda amount: replay(a, due, 0, amount)["funded"])
        result = no_saving
    else:
        contribution = minimum_amount(lambda amount: replay(a, due, amount)["funded"])
        additional = 0
        result = replay(a, due, contribution)
    possible = contribution is not None
    budget = a["monthly_budget_cents"]
    return {
        "monthly_plan_possible": possible,
        "reason": "funded" if possible else "upfront_funding_gap",
        "minimum_monthly_contribution_cents": contribution,
        "projected_savings_at_enrollment_cents": result["enrollment_balance"],
        "projected_total_college_cost_cents": sum(due.values()),
        "projected_balance_after_final_payment_cents": result["final_balance"],
        "additional_savings_needed_now_cents": additional,
        "first_shortfall_month": result["first_shortfall_month"],
        "fits_monthly_budget": None if budget is None else possible and contribution <= budget,
        "monthly_budget_shortfall_cents": None if budget is None or not possible else max(0, contribution - budget),
        "assumptions": a,
        "defaults_applied": defaults,
    }
