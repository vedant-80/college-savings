"""Independent Decimal replay and a minimality certificate, not a second binary search."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from plugin.data import scenario

def validate_arguments(args):
    if type(args) is not dict or set(args) != {'scenario_id'}:
        raise ValueError('Expected scenario_id')
    scenario(args['scenario_id'])

def replay(fixture, monthly):
    with localcontext() as context:
        context.prec = 60
        return _replay(fixture, monthly)

def _replay(fixture, monthly):
    costs = fixture['costs']
    account = fixture['account']
    def round_cent(n):
        return int(n.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    fees = {}
    components = [costs['annual_tuition_cents'], costs['annual_housing_cents']]
    for year in range(costs['program_years']):
        fees[costs['enrollment_month'] + year*12] = sum(components)
        components = [round_cent(Decimal(x) * (10000+costs['annual_cost_increase_bps']) / 10000) for x in components]
    balance = account['starting_balance_cents']
    rows, failed = [], 0
    end_month = costs['enrollment_month'] + costs['program_years']*12 - 1
    for m in range(1, end_month+1):
        earnings = round_cent(Decimal(balance) * account['monthly_return_bps'] / 10000)
        saving = monthly if m < costs['enrollment_month'] else 0
        scholarship = sum(a['amount_cents'] for a in fixture['scholarships']['awards'] if a['month'] == m)
        ending = balance + earnings + saving + scholarship - fees.get(m, 0)
        rows.append({'month': m, 'opening_balance_cents': balance, 'growth_cents': earnings,
                     'contribution_cents': saving, 'scholarship_cents': scholarship,
                     'expense_cents': fees.get(m, 0), 'closing_balance_cents': ending})
        balance = ending
        if ending < 0:
            failed = m
            break
    return rows, failed

def expected(args):
    raise RuntimeError('College verification uses the submitted minimality certificate')

def check_result(args, output):
    fixture = scenario(args['scenario_id'])
    contribution = output['monthly_contribution_cents']
    cap = fixture['account']['max_monthly_contribution_cents']
    if type(contribution) is not int or not 0 <= contribution <= cap:
        raise ValueError('Contribution outside permitted range')
    rows, failure = replay(fixture, contribution)
    if failure:
        if contribution != cap:
            raise ValueError('Infeasibility must be demonstrated at the cap')
    elif contribution > 0 and replay(fixture, contribution-1)[1] == 0:
        raise ValueError('Contribution is sufficient but not minimal')
    return {'scenario_id': args['scenario_id'], 'feasible': not failure,
            'monthly_contribution_cents': contribution, 'first_shortfall_month': failure,
            'final_balance_cents': rows[-1]['closing_balance_cents'], 'schedule': rows}
