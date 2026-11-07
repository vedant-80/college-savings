"""Typed custom college inputs and compact verified outputs; null explicitly selects defaults."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    CALCULATE = "calculate_college_savings"


class Task(Enum):
    CALCULATE = "plan-college-savings"


@dataclass
class CollegeInput(Output):
    months_until_enrollment: Annotated[
        int,
        "Whole months until enrollment (0 to 360); ask if missing. N months means N month-end deposits before the first bill.",
    ]
    current_savings_cents: Annotated[int, "Current college savings in integer cents; ask if missing. Use one currency."]
    annual_college_cost_cents: Annotated[
        int,
        "Annual all-in college cost in today's money, integer cents; ask if missing. Include tuition/housing as desired.",
    ]
    college_years: Annotated[int, "Number of annual college bills (1 to 10); ask if missing."]
    investment_return_bps: Annotated[
        int | None,
        "Nominal annual investment return in basis points; null defaults to 500 (5%). Monthly return = annual rate / 12.",
    ]
    cost_inflation_bps: Annotated[
        int | None,
        "Annual college-cost inflation in basis points; null defaults to 400 (4%). Applied at 12-month anniversaries from today.",
    ]
    monthly_budget_cents: Annotated[
        int | None,
        "Optional affordable monthly contribution in cents; null means no budget supplied, not a cap on the required amount.",
    ]


@dataclass
class CollegeAssumptions(Output):
    months_until_enrollment: Annotated[
        int,
        "Whole months until enrollment (0 to 360); ask if missing. N months means N month-end deposits before the first bill.",
    ]
    current_savings_cents: Annotated[int, "Current college savings in integer cents; ask if missing. Use one currency."]
    annual_college_cost_cents: Annotated[
        int,
        "Annual all-in college cost in today's money, integer cents; ask if missing. Include tuition/housing as desired.",
    ]
    college_years: Annotated[int, "Number of annual college bills (1 to 10); ask if missing."]
    investment_return_bps: Annotated[
        int,
        "Nominal annual investment return in basis points; null defaults to 500 (5%). Monthly return = annual rate / 12.",
    ]
    cost_inflation_bps: Annotated[
        int,
        "Annual college-cost inflation in basis points; null defaults to 400 (4%). Applied at 12-month anniversaries from today.",
    ]
    monthly_budget_cents: Annotated[
        int | None,
        "Optional affordable monthly contribution in cents; null means no budget supplied, not a cap on the required amount.",
    ]


@dataclass
class CollegeOutput(Output):
    monthly_plan_possible: Annotated[
        bool,
        "Whether a fixed monthly contribution can fund all annual bills; true also when zero contributions suffice.",
    ]
    reason: Annotated[str, "funded or upfront_funding_gap. Affordability is reported separately."]
    minimum_monthly_contribution_cents: Annotated[
        int | None, "Smallest contribution in whole cents; null when enrollment today leaves an upfront funding gap."
    ]
    projected_savings_at_enrollment_cents: Annotated[
        int, "Account balance immediately before the first annual bill, including the final pre-enrollment deposit."
    ]
    projected_total_college_cost_cents: Annotated[
        int, "Sum of every inflation-adjusted annual college bill, not a present value."
    ]
    projected_balance_after_final_payment_cents: Annotated[
        int | None,
        "Remaining savings immediately after the final annual bill; null if the current situation cannot fund all bills.",
    ]
    additional_savings_needed_now_cents: Annotated[
        int,
        "Minimum extra savings needed today when enrollment is immediate and unfunded; zero otherwise under the proposed monthly plan.",
    ]
    first_shortfall_month: Annotated[
        int | None, "First unfunded bill month, measured from today (0 means now); null for a funded monthly plan."
    ]
    fits_monthly_budget: Annotated[
        bool | None,
        "Whether the minimum plan fits the supplied budget; null if no budget was given, false for an upfront funding gap.",
    ]
    monthly_budget_shortfall_cents: Annotated[
        int | None,
        "Amount the monthly minimum exceeds the budget; null without a budget or without a possible monthly plan.",
    ]
    assumptions: Annotated[
        CollegeAssumptions, "All effective input values, including default rates and the optional budget."
    ]
    defaults_applied: Annotated[
        list[str], "Nullable rate fields that used defaults. Missing budget stays null; it is not a defaulted rate."
    ]


TOOLS = {Tool.CALCULATE: (CollegeInput, CollegeOutput)}
TASKS = {Task.CALCULATE: (CollegeInput, CollegeOutput)}
