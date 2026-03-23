"""Core implementation for `run_tests` in the Aura assistant project."""

import argparse
import sys
import unittest


SUITES = {
    "build": "tests.test_build_compile",
    "command_registry": "tests.test_command_registry",
    "short_memory": "tests.test_conversation_history",
    "long_memory": "tests.test_memory_manager",
    "system_commands": "tests.test_system_commands",
    "llm": "tests.test_llm_handler",
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
