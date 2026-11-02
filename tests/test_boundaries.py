import copy
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from plugin import calculations
from plugin.data import scenarios
from verifier import oracle
import verifier

class CollegeBoundaryTests(unittest.TestCase):
    def test_zero_growth_has_exact_minimum(self):
        out = calculations.solve({'scenario_id': 'zero-growth'})
        self.assertTrue(out['feasible'])
        self.assertEqual(out['monthly_contribution_cents'], 10000)
        self.assertEqual(out['final_balance_cents'], 0)
        self.assertEqual(len(out['schedule']), 24)
        self.assertEqual(out['schedule'][11]['contribution_cents'], 10000)
        self.assertEqual(out['schedule'][12]['contribution_cents'], 0)

    def test_rejects_sufficient_but_nonminimal_contribution(self):
        item = scenarios()['zero-growth']
        rows, failure = calculations.project(item, 10001)
        out = {'scenario_id': 'zero-growth', 'feasible': True, 'monthly_contribution_cents': 10001,
               'first_shortfall_month': failure, 'final_balance_cents': rows[-1]['closing_balance_cents'], 'schedule': rows}
        self.assertFalse(verifier.verify_task('plan-college-savings', {'scenario_id': 'zero-growth'}, out, None, ROOT)['valid'])

    def test_existing_savings_and_same_month_scholarship(self):
        self.assertEqual(calculations.solve({'scenario_id': 'already-funded'})['monthly_contribution_cents'], 0)
        funded = calculations.solve({'scenario_id': 'scholarship-funded'})
        self.assertTrue(funded['feasible'])
        self.assertEqual(funded['monthly_contribution_cents'], 0)
        self.assertEqual(funded['final_balance_cents'], 5000)

    def test_late_scholarship_cannot_repair_an_earlier_shortfall(self):
        out = calculations.solve({'scenario_id': 'late-scholarship'})
        self.assertFalse(out['feasible'])
        self.assertEqual(out['first_shortfall_month'], 2)
        self.assertEqual(len(out['schedule']), 2)

    def test_infeasibility_is_shown_at_contribution_cap(self):
        out = calculations.solve({'scenario_id': 'cap-insufficient'})
        self.assertFalse(out['feasible'])
        self.assertEqual(out['monthly_contribution_cents'], 100)
        self.assertEqual(out['final_balance_cents'], -99800)

    def test_seeded_replay_and_minimality(self):
        rng = random.Random(20261102)
        for _ in range(100):
            fixture = copy.deepcopy(scenarios()['five-year-start'])
            fixture['costs'].update(enrollment_month=rng.randrange(1,30),program_years=rng.randrange(1,5),
                                   annual_tuition_cents=rng.randrange(0,1000000),annual_housing_cents=rng.randrange(0,1000000))
            fixture['account'].update(starting_balance_cents=rng.randrange(0,1000000),
                                     max_monthly_contribution_cents=rng.randrange(0,1000000),monthly_return_bps=rng.randrange(0,1000))
            fixture['scholarships']['awards'] = []
            with patch.object(calculations, 'scenario', return_value=fixture), patch.object(oracle, 'scenario', return_value=fixture):
                args = {'scenario_id': 'random'}
                out = calculations.solve(args)
                self.assertEqual(out, oracle.check_result(args, out))
