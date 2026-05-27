"""Core implementation for `run_tests` in the Aura assistant project."""

import argparse
import sys
import unittest


SUITES = {
    "build": "testing.tests.test_build_compile",
    "runtime_smoke": "testing.tests.test_runtime_smoke",
    "config": "testing.tests.test_config_loader",
    "logger": "testing.tests.test_logger",
    "sqlite": "testing.tests.test_sqlite_database",
    "datetime_utils": "testing.tests.test_datetime_utils",
    "autonomous_tasks": "testing.tests.test_autonomous_tasks",
    "context_awareness": "testing.tests.test_context_awareness",
    "observability": "testing.tests.test_observability",
    "events": "testing.tests.test_events",
    "notifications": "testing.tests.test_notifications",
    "system": "testing.tests.test_system",
    "short_memory": "testing.tests.test_conversation_history",
    "long_memory": "testing.tests.test_memory_manager",
    "calendar": "testing.tests.test_calendar",
    "interfaces": ("testing.tests.interfaceTests", "testing.tests.test_developer_ui"),
    "developer_ui": "testing.tests.test_developer_ui",
    "home_automation": "testing.tests.test_home_automation",
    "module_loader": "testing.tests.test_module_loader",
    "tools": "testing.tests.test_tool_system",
    "intent_pipeline": "testing.tests.test_intent_pipeline",
    "llm": "testing.tests.test_llm_handler",
    "prompts": "testing.tests.test_prompt_builder",
    "voice": "testing.tests.test_voice",
    "assistant_testing": "testing.tests.test_assistant_testing",
    "reminders": "testing.tests.test_reminders",
    "mysql_integration": "testing.tests.test_mysql_integration",
}


def parse_args():
    """Parse command-line arguments for selecting test execution behavior."""
    parser = argparse.ArgumentParser(
        description="Run Aura test suites."
    )
    parser.add_argument(
        "--suite",
        choices=["all"] + list(SUITES.keys()),
        default="all",
        help="Choose a specific suite or run all suites.",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        default=2,
        choices=[0, 1, 2],
        help="unittest verbosity level",
    )
    return parser.parse_args()


def main():
    """Run the primary entrypoint logic for this script/module."""
    args = parse_args()
    loader = unittest.TestLoader()

    if args.suite == "all":
        suite = unittest.TestSuite()
        for module_name in SUITES.values():
            for target in _suiteTargets(module_name):
                suite.addTests(loader.loadTestsFromName(target))
    else:
        suite = unittest.TestSuite()
        for target in _suiteTargets(SUITES[args.suite]):
            suite.addTests(loader.loadTestsFromName(target))

    runner = unittest.TextTestRunner(verbosity=args.verbosity)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def _suiteTargets(value):
    """Return one or more unittest load targets for a configured suite."""

    if isinstance(value, (tuple, list)):
        return tuple(value)
    return (value,)


if __name__ == "__main__":
    sys.exit(main())
