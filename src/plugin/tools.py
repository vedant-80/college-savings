"""Read-only scenario tools. None calculates the task's final answer."""
import json
from importlib.resources import files
from .data import scenario, field

def get_rules(value, workspace):
    """Retrieve the precise fictional financial rules and rounding conventions."""
    return json.loads(files('plugin').joinpath('data/rules.json').read_text())


def get_college_costs(value, workspace):
    """Retrieve enrollment timing, cost components, and annual cost increases."""
    return scenario(field(value, 'scenario_id'))['costs']

def get_savings_account(value, workspace):
    """Retrieve initial savings, monthly return, and contribution limit."""
    return scenario(field(value, 'scenario_id'))['account']

def get_scholarships(value, workspace):
    """Retrieve every scholarship disbursement month and amount."""
    return scenario(field(value, 'scenario_id'))['scholarships']


IMPLEMENTATIONS = {'get_college_costs': get_college_costs, 'get_savings_account': get_savings_account, 'get_scholarships': get_scholarships, 'get_rules': get_rules}
