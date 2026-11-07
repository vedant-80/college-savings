import copy
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from plugin.calculations import bills, normalize, replay, solve
from verifier.oracle import check_result


def example(**changes):
    return json.loads((ROOT / "tests/example.json").read_text()) | changes


def simple(**changes):
    return (
        example(
            months_until_enrollment=12,
            current_savings_cents=0,
            annual_college_cost_cents=1200,
            college_years=1,
            investment_return_bps=0,
            cost_inflation_bps=0,
            monthly_budget_cents=None,
        )
        | changes
    )


class CollegeCalculationTests(unittest.TestCase):
    def test_custom_input_defaults_and_compact_output(self):
        result = solve(example())
        self.assertTrue(result["monthly_plan_possible"])
        self.assertEqual(result["assumptions"]["investment_return_bps"], 500)
        self.assertEqual(result["assumptions"]["cost_inflation_bps"], 400)
        self.assertEqual(result["defaults_applied"], ["investment_return_bps", "cost_inflation_bps"])
        self.assertLess(len(json.dumps(result)), 2000)
        self.assertNotIn("schedule", result)
        self.assertEqual(check_result(example(), result), result)

    def test_zero_return_exact_minimum_and_last_deposit_before_bill(self):
        out = solve(simple())
        self.assertEqual(out["minimum_monthly_contribution_cents"], 100)
        self.assertEqual(out["projected_savings_at_enrollment_cents"], 1200)
        self.assertEqual(out["projected_balance_after_final_payment_cents"], 0)
        self.assertEqual(out["projected_total_college_cost_cents"], 1200)
        self.assertIsNone(out["first_shortfall_month"])
        self.assertEqual(out["defaults_applied"], [])

    def test_contributions_stop_at_enrollment(self):
        out = solve(simple(college_years=2))
        self.assertEqual(out["minimum_monthly_contribution_cents"], 200)
        self.assertEqual(out["projected_savings_at_enrollment_cents"], 2400)
        self.assertEqual(out["projected_total_college_cost_cents"], 2400)
        self.assertEqual(out["projected_balance_after_final_payment_cents"], 0)

    def test_growth_precedes_deposit_and_monthly_half_cent_rounds_up(self):
        args = simple(
            months_until_enrollment=1,
            current_savings_cents=100,
            annual_college_cost_cents=202,
            investment_return_bps=600,
        )
        # 100 cents earns 0.5 cents -> 1; deposit 101 arrives after growth, then bill 202.
        out = solve(args)
        self.assertEqual(out["minimum_monthly_contribution_cents"], 101)
        self.assertEqual(out["projected_savings_at_enrollment_cents"], 202)
        self.assertEqual(out["projected_balance_after_final_payment_cents"], 0)

    def test_cost_inflates_at_anniversary_before_bill_and_not_fractional_year(self):
        for month, cost in ((11, 1000), (12, 1100), (18, 1100), (24, 1210)):
            args = simple(months_until_enrollment=month, annual_college_cost_cents=1000, cost_inflation_bps=1000)
            with self.subTest(month=month):
                self.assertEqual(solve(args)["projected_total_college_cost_cents"], cost)
        out = solve(simple(annual_college_cost_cents=1, cost_inflation_bps=5000, college_years=2))
        # First bill 1 + rounded(0.5)=2; second bill 2 + rounded(1)=3.
        self.assertEqual(out["projected_total_college_cost_cents"], 5)

    def test_immediate_enrollment_and_minimal_upfront_gap(self):
        args = simple(months_until_enrollment=0, current_savings_cents=500, college_years=2)
        out = solve(args)
        self.assertFalse(out["monthly_plan_possible"])
        self.assertEqual(out["reason"], "upfront_funding_gap")
        self.assertIsNone(out["minimum_monthly_contribution_cents"])
        self.assertEqual(out["additional_savings_needed_now_cents"], 1900)
        self.assertEqual(out["first_shortfall_month"], 0)
        self.assertEqual(out["projected_savings_at_enrollment_cents"], 500)
        self.assertIsNone(out["projected_balance_after_final_payment_cents"])
        self.assertEqual(check_result(args, out), out)
        for change in (-1, 1):
            with self.assertRaises(ValueError):
                check_result(args, out | {"additional_savings_needed_now_cents": 1900 + change})

    def test_upfront_gap_can_occur_at_a_later_bill(self):
        args = simple(
            months_until_enrollment=0, current_savings_cents=1500, college_years=2, monthly_budget_cents=999999
        )
        out = solve(args)
        self.assertEqual(out["first_shortfall_month"], 12)
        self.assertEqual(out["additional_savings_needed_now_cents"], 900)
        self.assertFalse(out["fits_monthly_budget"])
        self.assertIsNone(out["monthly_budget_shortfall_cents"])

    def test_already_funded_and_zero_cost(self):
        for months in (0, 12):
            out = solve(simple(months_until_enrollment=months, current_savings_cents=2400, college_years=2))
            self.assertTrue(out["monthly_plan_possible"])
            self.assertEqual(out["minimum_monthly_contribution_cents"], 0)
            self.assertEqual(out["additional_savings_needed_now_cents"], 0)
        out = solve(simple(annual_college_cost_cents=0))
        self.assertEqual(out["minimum_monthly_contribution_cents"], 0)

    def test_budget_never_changes_minimum(self):
        for budget, fit, gap in ((None, None, None), (0, False, 100), (99, False, 1), (100, True, 0), (101, True, 0)):
            out = solve(simple(monthly_budget_cents=budget))
            self.assertEqual(out["minimum_monthly_contribution_cents"], 100)
            self.assertEqual(out["fits_monthly_budget"], fit)
            self.assertEqual(out["monthly_budget_shortfall_cents"], gap)
            self.assertEqual(out["assumptions"]["monthly_budget_cents"], budget)

    def test_verifier_rejects_insufficient_and_nonminimal_contributions(self):
        args = simple()
        answer = solve(args)
        for amount in (99, 101):
            with self.assertRaises(ValueError):
                check_result(args, answer | {"minimum_monthly_contribution_cents": amount})

    def test_negative_return_rounding_and_remaining_growth_during_college(self):
        args = simple(
            months_until_enrollment=0,
            current_savings_cents=2000,
            annual_college_cost_cents=1000,
            college_years=2,
            investment_return_bps=-6000,
        )
        out = solve(args)
        self.assertEqual(check_result(args, out), out)
        self.assertGreater(out["additional_savings_needed_now_cents"], 0)
        args = simple(
            months_until_enrollment=0,
            current_savings_cents=2000,
            annual_college_cost_cents=1000,
            college_years=2,
            investment_return_bps=1200,
        )
        out = solve(args)
        self.assertEqual(out["minimum_monthly_contribution_cents"], 0)
        self.assertGreater(out["projected_balance_after_final_payment_cents"], 0)

    def test_small_cases_match_exhaustive_search(self):
        rng = random.Random(1303)
        for _ in range(100):
            args = simple(
                months_until_enrollment=rng.randrange(1, 5),
                current_savings_cents=rng.randrange(20),
                annual_college_cost_cents=rng.randrange(1, 20),
                college_years=rng.randrange(1, 3),
                investment_return_bps=rng.choice((-10000, 0, 500, 10000)),
            )
            a, _ = normalize(args)
            due = bills(a)
            brute = next(c for c in range(1000) if replay(a, due, c)["funded"])
            result = solve(args)
            self.assertEqual(result["minimum_monthly_contribution_cents"], brute)
            self.assertEqual(check_result(args, result), result)

    def test_seeded_custom_cases_and_extreme_bounds_have_valid_certificates(self):
        rng = random.Random(1304)
        for _ in range(150):
            args = example(
                months_until_enrollment=rng.randrange(37),
                current_savings_cents=rng.randrange(1000000),
                annual_college_cost_cents=rng.randrange(1000000),
                college_years=rng.randrange(1, 5),
                investment_return_bps=rng.randrange(-10000, 10001),
                cost_inflation_bps=rng.randrange(10001),
                monthly_budget_cents=rng.choice((None, 0, 1000, 1000000)),
            )
            result = solve(args)
            self.assertEqual(check_result(args, result), result)
        for months in (0, 360):
            for rate in (-10000, 10000):
                args = example(
                    months_until_enrollment=months,
                    current_savings_cents=10**15,
                    annual_college_cost_cents=10**15,
                    college_years=10,
                    investment_return_bps=rate,
                    cost_inflation_bps=10000,
                )
                result = solve(args)
                self.assertEqual(check_result(args, result), result)
                self.assertLess(len(json.dumps(result)), 2000)

    def test_calculation_does_not_mutate_input(self):
        args = example()
        saved = copy.deepcopy(args)
        solve(args)
        self.assertEqual(args, saved)
