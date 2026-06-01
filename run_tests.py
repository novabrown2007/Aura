"""Core implementation for `run_tests` in the Aura assistant project."""

import argparse
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SUITES = {
    "build": "testing.tests.test_build_compile",
    "runtime_smoke": "testing.tests.test_runtime_smoke",
    "config": "testing.tests.test_config_loader",
    "logger": "testing.tests.test_logger",
    "sqlite": "testing.tests.test_sqlite_database",
    "datetime_utils": "testing.tests.test_datetime_utils",
    "autonomous_tasks": "testing.tests.test_autonomous_tasks",
    "automation_composer": "testing.tests.test_automation_composer",
    "threading_scheduler": "testing.tests.test_threading_scheduler",
    "async_tasks": "testing.tests.test_async_tasks",
    "context_awareness": "testing.tests.test_context_awareness",
    "conversation_continuity": "testing.tests.test_conversation_continuity",
    "clarification": "testing.tests.test_clarification",
    "personality": "testing.tests.test_personality",
    "weather": "testing.tests.test_weather_module",
    "spotify": "testing.tests.test_spotify_module",
    "email": (
        "testing.tests.modules.email.testEmailAccounts",
        "testing.tests.modules.email.testInboxReading",
        "testing.tests.modules.email.testEmailDrafts",
        "testing.tests.modules.email.testEmailScheduling",
        "testing.tests.modules.email.testEmailFiltering",
        "testing.tests.modules.email.testEmailNotifications",
        "testing.tests.modules.email.testEmailSafety",
        "testing.tests.modules.email.testEmailProviders",
    ),
    "semantic_memory": "testing.tests.test_semantic_memory",
    "execution": "testing.tests.test_execution_pipeline",
    "module_framework": "testing.tests.test_module_framework",
    "observability": "testing.tests.test_observability",
    "events": "testing.tests.test_events",
    "bridge_protocol": "testing.tests.test_bridge_protocol",
    "notifications": "testing.tests.test_notifications",
    "system": "testing.tests.test_system",
    "short_memory": "testing.tests.test_conversation_history",
    "long_memory": "testing.tests.test_memory_manager",
    "memory_retrieval": "testing.tests.test_memory_retrieval",
    "home_automation": "testing.tests.test_home_automation",
    "module_loader": "testing.tests.test_module_loader",
    "tools": "testing.tests.test_tool_system",
    "intent_pipeline": "testing.tests.test_intent_pipeline",
    "llm": "testing.tests.test_llm_handler",
    "prompts": "testing.tests.test_prompt_builder",
    "assistant_testing": "testing.tests.test_assistant_testing",
    "personal_schedule": "testing.tests.test_personal_schedule",
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
    suite = buildSuite(args.suite)

    runner = unittest.TextTestRunner(verbosity=args.verbosity)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def buildSuite(suiteName: str):
    """Build a unittest suite using discovery for all tests or a named target."""

    loader = unittest.TestLoader()
    if suiteName == "all":
        return loader.discover("testing/tests", top_level_dir=str(ROOT))

    suite = unittest.TestSuite()
    for target in _suiteTargets(SUITES[suiteName]):
        suite.addTests(loader.loadTestsFromName(target))
    return suite


def _suiteTargets(value):
    """Return one or more unittest load targets for a configured suite."""

    if isinstance(value, (tuple, list)):
        return tuple(value)
    return (value,)


if __name__ == "__main__":
    sys.exit(main())
