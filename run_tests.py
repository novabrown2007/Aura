"""Core implementation for `run_tests` in the Aura assistant project."""

import argparse
import sys
import unittest


SUITES = {
    "build": "tests.test_build_compile",
    "runtime_smoke": "tests.test_runtime_smoke",
    "logger": "tests.test_logger",
    "datetime_utils": "tests.test_datetime_utils",
    "notifications": "tests.test_notifications",
    "database_factory": "tests.test_database_factory",
    "system": "tests.test_system",
    "windows_interface": "tests.test_windows_interface",
    "short_memory": "tests.test_conversation_history",
    "long_memory": "tests.test_memory_manager",
    "calendar": "tests.test_calendar",
    "llm": "tests.test_llm_handler",
    "reminders": "tests.test_reminders",
    "mysql_integration": "tests.test_mysql_integration",
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
            suite.addTests(loader.loadTestsFromName(module_name))
    else:
        suite = loader.loadTestsFromName(SUITES[args.suite])

    runner = unittest.TextTestRunner(verbosity=args.verbosity)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
