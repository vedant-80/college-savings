"""Deterministic checks; no model calls, tool-output trust, or reference-answer dependence."""
from dataclasses import asdict, is_dataclass
from functools import partial
from types import SimpleNamespace
from plugin.data import scenario
from plugin.tools import IMPLEMENTATIONS
from .oracle import check_result, validate_arguments

TOOL_NAMES = ['get_college_costs', 'get_savings_account', 'get_scholarships', 'get_rules']
TASK_NAME = 'plan-college-savings'

def plain(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain(v) for v in value]
    return value

def same(actual, wanted):
    # Reject bool-as-int, float-as-int, omitted/extra fields, and reordered rows.
    if type(actual) is not type(wanted):
        return False
    if isinstance(wanted, dict):
        return actual.keys() == wanted.keys() and all(same(actual[k], v) for k, v in wanted.items())
    if isinstance(wanted, list):
        return len(actual) == len(wanted) and all(same(a, b) for a, b in zip(actual, wanted))
    return actual == wanted

def verdict(valid, message):
    return {'valid': valid, 'score': float(valid), 'message': message, 'details': {}}

def tool_name(tool):
    return tool.value if hasattr(tool, 'value') else tool

def verify_input(tool, value):
    try:
        name = tool_name(tool)
        if name not in TOOL_NAMES:
            raise ValueError('Unknown tool')
        args = plain(value)
        if name == 'get_rules':
            if args != {}:
                raise ValueError('get_rules takes no arguments')
        else:
            if set(args) != {'scenario_id'}:
                raise ValueError('Expected only scenario_id')
            scenario(args['scenario_id'])
        return verdict(True, 'Valid tool input')
    except (ValueError, KeyError, TypeError, AttributeError):
        return verdict(False, 'Invalid tool input')

def verify_output(tool, input_value, output_value, workspace):
    check = verify_input(tool, input_value)
    if not check['valid']:
        return check
    try:
        wanted = IMPLEMENTATIONS[tool_name(tool)](plain(input_value), None)
        valid = same(plain(output_value), wanted)
        return verdict(valid, 'Tool output matches fixture' if valid else 'Tool output differs from fixture')
    except (ValueError, KeyError, TypeError, AttributeError):
        return verdict(False, 'Missing or malformed tool output')

def verify_task(task, arguments, output, reference, workspace):
    try:
        if tool_name(task) != TASK_NAME:
            raise ValueError('Unknown task')
        args = plain(arguments)
        validate_arguments(args)
        wanted = check_result(args, plain(output))
        valid = same(plain(output), wanted)
        return verdict(valid, 'All financial results match independent replay' if valid
                       else 'Output differs from independent replay (including required rows and totals)')
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return verdict(False, 'Missing, malformed, or invalid task input/output')

# Tool/task dispatch remains available through the public functions above.
TOOLS = {name: SimpleNamespace(verify_input=partial(verify_input, name),
                               verify_output=partial(verify_output, name)) for name in TOOL_NAMES}
TASKS = {TASK_NAME: partial(verify_task, TASK_NAME)}
