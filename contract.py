"""Typed tool and task declarations; money is always integer cents."""
from dataclasses import dataclass
from enum import Enum
from slimconfig import Output

@dataclass
class ScenarioInput(Output):
    scenario_id: str

@dataclass
class RulesInput(Output):
    pass

@dataclass
class RulesOutput(Output):
    rules: list[str]

class Tool(Enum):
    GET_COLLEGE_COSTS = 'get_college_costs'
    GET_SAVINGS_ACCOUNT = 'get_savings_account'
    GET_SCHOLARSHIPS = 'get_scholarships'
    GET_RULES = 'get_rules'

class Task(Enum):
    PLAN_COLLEGE_SAVINGS = 'plan-college-savings'

@dataclass
class CostsOutput(Output):
    enrollment_month: int
    program_years: int
    annual_tuition_cents: int
    annual_housing_cents: int
    annual_cost_increase_bps: int

@dataclass
class SavingsOutput(Output):
    starting_balance_cents: int
    monthly_return_bps: int
    max_monthly_contribution_cents: int

@dataclass
class Scholarship(Output):
    month: int
    amount_cents: int

@dataclass
class ScholarshipsOutput(Output):
    awards: list[Scholarship]

@dataclass
class CollegeMonth(Output):
    month: int
    opening_balance_cents: int
    growth_cents: int
    contribution_cents: int
    scholarship_cents: int
    expense_cents: int
    closing_balance_cents: int

@dataclass
class CollegeOutput(Output):
    scenario_id: str
    feasible: bool
    monthly_contribution_cents: int
    first_shortfall_month: int
    final_balance_cents: int
    schedule: list[CollegeMonth]

TOOLS = {
    Tool.GET_COLLEGE_COSTS: (ScenarioInput, CostsOutput),
    Tool.GET_SAVINGS_ACCOUNT: (ScenarioInput, SavingsOutput),
    Tool.GET_SCHOLARSHIPS: (ScenarioInput, ScholarshipsOutput),
    Tool.GET_RULES: (RulesInput, RulesOutput),
}
TASKS = {Task.PLAN_COLLEGE_SAVINGS: (ScenarioInput, CollegeOutput)}
