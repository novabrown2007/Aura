"""Shared parsing and formatting helpers for calendar CLI commands."""

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
        value = yaml.safe_load(raw_value)
        if isinstance(value, str) and "," in value and key in {"attendees", "categories"}:
            value = [part.strip() for part in value.split(",") if part.strip()]
        parsed[key] = value
    return parsed


def format_result(value):
    """Format dict/list command output as readable JSON."""

    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, sort_keys=True, default=str)
    return str(value)
