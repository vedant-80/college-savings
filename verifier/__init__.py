"""Deterministic verification of custom inputs and compact calculator outputs."""

from dataclasses import asdict, is_dataclass

from .oracle import check_result, normalize

TOOL_NAME = "calculate_college_savings"
TASK_NAME = "plan-college-savings"


def plain(value):
    return asdict(value) if is_dataclass(value) else value


def same(actual, wanted):
    if type(actual) is not type(wanted):
        return False
    if isinstance(wanted, dict):
        return actual.keys() == wanted.keys() and all(same(actual[k], v) for k, v in wanted.items())
    if isinstance(wanted, list):
        return len(actual) == len(wanted) and all(same(a, b) for a, b in zip(actual, wanted))
    return actual == wanted


def named(value):
    return value.value if hasattr(value, "value") else value


def verdict(valid, message):
    return {"valid": valid, "score": float(valid), "message": message, "details": {}}


def verify_input(tool, value):
    try:
        if named(tool) != TOOL_NAME:
            raise ValueError("Unknown calculation tool")
        normalize(value)
        return verdict(True, "Valid calculation input")
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        return verdict(False, str(error))


def verify_output(tool, input_value, output_value, workspace):
    check = verify_input(tool, input_value)
    if not check["valid"]:
        return check
    try:
        valid = same(plain(output_value), check_result(input_value, plain(output_value)))
        return verdict(
            valid, "Matches independent replay" if valid else "Result or assumptions differ from independent replay"
        )
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return verdict(False, "Malformed calculation result")


def verify_task(task, arguments, output, reference, workspace):
    if named(task) != TASK_NAME:
        return verdict(False, "Unknown task")
    return verify_output(TOOL_NAME, arguments, output, workspace)
