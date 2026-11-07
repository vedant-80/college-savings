"""One deterministic calculation tool with compact results."""

from .calculations import solve


def calculate_college_savings(value, workspace):
    """Find the minimum monthly contribution and evaluate an optional budget entirely in Python."""
    return solve(value)


IMPLEMENTATIONS = {"calculate_college_savings": calculate_college_savings}
