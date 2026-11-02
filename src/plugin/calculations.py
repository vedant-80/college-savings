"""Offline demonstration using integer replay and binary search for minimum saving."""
from .data import scenario

def rounded(value):
    return (2 * value + 10000) // 20000

def project(item, contribution):
    costs, account = item['costs'], item['account']
    expense = {}
    tuition, housing = costs['annual_tuition_cents'], costs['annual_housing_cents']
    for year in range(costs['program_years']):
        expense[costs['enrollment_month'] + 12 * year] = tuition + housing
        tuition = rounded(tuition * (10000 + costs['annual_cost_increase_bps']))
        housing = rounded(housing * (10000 + costs['annual_cost_increase_bps']))
    awards = {}
    for award in item['scholarships']['awards']:
        awards[award['month']] = awards.get(award['month'], 0) + award['amount_cents']
    balance, history, failure = account['starting_balance_cents'], [], 0
    horizon = costs['enrollment_month'] + 12 * costs['program_years'] - 1
    for month in range(1, horizon + 1):
        growth = rounded(balance * account['monthly_return_bps'])
        deposit = contribution if month < costs['enrollment_month'] else 0
        end = balance + growth + deposit + awards.get(month, 0) - expense.get(month, 0)
        history.append(dict(month=month, opening_balance_cents=balance, growth_cents=growth,
                            contribution_cents=deposit, scholarship_cents=awards.get(month, 0),
                            expense_cents=expense.get(month, 0), closing_balance_cents=end))
        balance = end
        if end < 0:
            failure = month
            break
    return history, failure

def solve(arguments):
    item = scenario(arguments['scenario_id'])
    low, high = 0, item['account']['max_monthly_contribution_cents']
    _, failure = project(item, high)
    if not failure:
        while low < high:
            mid = (low+high)//2
            if project(item, mid)[1]:
                low = mid+1
            else:
                high = mid
    contribution = high
    rows, failure = project(item, contribution)
    return dict(scenario_id=arguments['scenario_id'], feasible=not failure,
                monthly_contribution_cents=contribution, first_shortfall_month=failure,
                final_balance_cents=rows[-1]['closing_balance_cents'], schedule=rows)
