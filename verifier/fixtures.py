"""Trusted verifier fixtures. Keep in sync with src/plugin/data; tests enforce equality."""

def scenarios():
    return {'already-funded': {'account': {'max_monthly_contribution_cents': 500000,
                                    'monthly_return_bps': 30,
                                    'starting_balance_cents': 20000000},
                        'costs': {'annual_cost_increase_bps': 300,
                                  'annual_housing_cents': 1200000,
                                  'annual_tuition_cents': 1800000,
                                  'enrollment_month': 61,
                                  'program_years': 4},
                        'scholarships': {'awards': []}},
     'cap-insufficient': {'account': {'max_monthly_contribution_cents': 100,
                                      'monthly_return_bps': 0,
                                      'starting_balance_cents': 0},
                          'costs': {'annual_cost_increase_bps': 300,
                                    'annual_housing_cents': 0,
                                    'annual_tuition_cents': 100000,
                                    'enrollment_month': 3,
                                    'program_years': 1},
                          'scholarships': {'awards': []}},
     'five-year-start': {'account': {'max_monthly_contribution_cents': 500000,
                                     'monthly_return_bps': 30,
                                     'starting_balance_cents': 2000000},
                         'costs': {'annual_cost_increase_bps': 300,
                                   'annual_housing_cents': 1200000,
                                   'annual_tuition_cents': 1800000,
                                   'enrollment_month': 61,
                                   'program_years': 4},
                         'scholarships': {'awards': [{'amount_cents': 500000, 'month': 61},
                                                     {'amount_cents': 500000, 'month': 73},
                                                     {'amount_cents': 500000, 'month': 85},
                                                     {'amount_cents': 500000, 'month': 97}]}},
     'immediate-shortfall': {'account': {'max_monthly_contribution_cents': 500000,
                                         'monthly_return_bps': 0,
                                         'starting_balance_cents': 0},
                             'costs': {'annual_cost_increase_bps': 300,
                                       'annual_housing_cents': 0,
                                       'annual_tuition_cents': 10000,
                                       'enrollment_month': 1,
                                       'program_years': 1},
                             'scholarships': {'awards': []}},
     'late-scholarship': {'account': {'max_monthly_contribution_cents': 0,
                                      'monthly_return_bps': 0,
                                      'starting_balance_cents': 0},
                          'costs': {'annual_cost_increase_bps': 300,
                                    'annual_housing_cents': 0,
                                    'annual_tuition_cents': 10000,
                                    'enrollment_month': 2,
                                    'program_years': 1},
                          'scholarships': {'awards': [{'amount_cents': 10000, 'month': 3}]}},
     'scholarship-funded': {'account': {'max_monthly_contribution_cents': 500000,
                                        'monthly_return_bps': 0,
                                        'starting_balance_cents': 0},
                            'costs': {'annual_cost_increase_bps': 300,
                                      'annual_housing_cents': 0,
                                      'annual_tuition_cents': 10000,
                                      'enrollment_month': 1,
                                      'program_years': 1},
                            'scholarships': {'awards': [{'amount_cents': 15000, 'month': 1}]}},
     'zero-growth': {'account': {'max_monthly_contribution_cents': 500000,
                                 'monthly_return_bps': 0,
                                 'starting_balance_cents': 0},
                     'costs': {'annual_cost_increase_bps': 0,
                               'annual_housing_cents': 0,
                               'annual_tuition_cents': 120000,
                               'enrollment_month': 13,
                               'program_years': 1},
                     'scholarships': {'awards': []}}}

def rules():
    return {'rules': ['Money is integer cents. Months are 1-based. monthly_return_bps is a fixed MONTHLY return, not an '
               'annual rate.',
               'Year 1 costs are annual_tuition_cents plus annual_housing_cents. Each subsequent academic year '
               'multiplies each prior component by 1 + annual_cost_increase_bps/10000, rounding each component '
               'to cents, ties up.',
               'Pay each academic year costs in full at enrollment_month + 12 * academic_year_index. Horizon '
               'ends at enrollment_month + 12 * program_years - 1.',
               'Each month: apply growth to opening savings (round to cents, ties up), add the fixed monthly '
               'contribution if month < enrollment_month, add scholarships, then pay expenses.',
               'Find the smallest nonnegative whole-cent monthly contribution at or below '
               'max_monthly_contribution_cents that never makes savings negative.',
               'If no allowed contribution works, feasible=false and monthly_contribution_cents must equal the '
               'cap. Return its projection through its first shortfall.',
               'If feasible, return the full projection through the horizon with first_shortfall_month=0. A '
               'failed projection stops at the first negative closing balance. No borrowing or taxes are '
               'modeled.']}

def scenario(identifier):
    items = scenarios()
    if type(identifier) is not str or identifier not in items:
        raise ValueError('Unknown scenario_id')
    return items[identifier]

def tool_output(name, arguments):
    if name == 'get_rules':
        return rules()
    item = scenario(arguments['scenario_id'])
    if name == 'get_college_costs':
        return item['costs']
    if name == 'get_savings_account':
        return item['account']
    if name == 'get_scholarships':
        return item['scholarships']
    raise ValueError('Unknown tool')
