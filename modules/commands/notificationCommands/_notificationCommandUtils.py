"""Shared parsing and formatting helpers for notification CLI commands."""

from __future__ import annotations

import json

import yaml


def parse_key_value_args(args):
    """Parse `key=value` CLI arguments into a dictionary."""

    parsed = {}
    for raw_arg in args:
        if "=" not in raw_arg:
            raise ValueError(f"Expected key=value argument, got: {raw_arg}")
        key, raw_value = raw_arg.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid key=value argument: {raw_arg}")
        parsed[key] = yaml.safe_load(raw_value)
    return parsed


def format_result(value):
    """Format dict and list results as readable JSON."""

    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, sort_keys=True, default=str)
    return str(value)
