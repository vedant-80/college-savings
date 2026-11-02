"""Read immutable packaged fixtures; scenario IDs are keys, never file paths."""
import json
from importlib.resources import files

def scenarios():
    return json.loads(files('plugin').joinpath('data/scenarios.json').read_text())

def scenario(identifier):
    if type(identifier) is not str or identifier not in scenarios():
        raise ValueError('Unknown scenario_id; see README.md for available scenarios')
    return scenarios()[identifier]

def field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)
