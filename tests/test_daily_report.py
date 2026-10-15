"""Include the bundled daily-report suite in repository-wide discovery."""
from pathlib import Path
import unittest


SKILL_TESTS = (Path(__file__).resolve().parents[1] / "plugins" / "context" /
               "skills" / "daily-report" / "tests")


def load_tests(loader, standard_tests, pattern):
    return unittest.TestLoader().discover(str(SKILL_TESTS), pattern="test_*.py")
