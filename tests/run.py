#!/usr/bin/env python3
"""Run SENTINEL's tests.

    ./sentinel test                     everything (browser tests too, if Playwright is installed)
    ./sentinel test --fast              skip the browser tests (seconds instead of a minute)
    ./sentinel test --case 02-echoes    only the tests for one case (what `case publish` runs)
    ./sentinel test --install-hook      run the fast tests before every git commit
"""
import argparse
import os
import shutil
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
VENV_PY = ROOT / ".venv" / "bin" / "python"


def has_playwright():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def flatten(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from flatten(t)
        else:
            yield t


def main():
    ap = argparse.ArgumentParser(prog="sentinel test")
    ap.add_argument("--fast", action="store_true", help="skip browser tests")
    ap.add_argument("--case", help="only test this case id (or 'tutorial')")
    ap.add_argument("--strict", action="store_true", help="hold the case(s) to published standards even if they're drafts")
    ap.add_argument("--install-hook", action="store_true", help="install a git pre-commit hook that runs the fast tests")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args()

    if a.install_hook:
        hook = ROOT / ".git" / "hooks" / "pre-commit"
        if not hook.parent.is_dir():
            sys.exit("no .git/hooks folder: is this a git repository?")
        if hook.exists() and "sentinel test" not in hook.read_text():
            sys.exit(f"{hook} already exists and isn't ours; not replacing it")
        shutil.copyfile(ROOT / "tools" / "hooks" / "pre-commit", hook)
        hook.chmod(0o755)
        print(f"Installed {hook.relative_to(ROOT)}: `git commit` now runs ./sentinel test --fast first.")
        return 0

    # Browser tests need Playwright, which lives in the project's .venv.
    if not a.fast and not has_playwright() and VENV_PY.exists() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])

    if a.case:
        os.environ["SENTINEL_TEST_CASE"] = a.case
    if a.strict:
        os.environ["SENTINEL_STRICT"] = "1"
    sys.path.insert(0, str(TESTS))
    loader = unittest.TestLoader()
    tests = list(flatten(loader.discover(str(TESTS), top_level_dir=str(TESTS))))
    errors = [t for t in tests if type(t).__name__ == "_FailedTest"]
    if a.fast:
        tests = [t for t in tests if not t.id().startswith("browser.")]
    if a.case:
        keep = ("test_cases.CaseContent", "test_cases.CaseApi", "browser.test_play_cases.PlayEveryCase")
        if a.case == "tutorial":
            keep += ("browser.test_tutorial",)
        tests = [t for t in tests if t.id().startswith(keep)] + [t for t in errors if t not in tests]
    browser = [t for t in tests if t.id().startswith("browser.")]
    if browser and not has_playwright():
        print("note: Playwright isn't installed, so browser tests will be skipped (see tests/README.md)\n")
    result = unittest.TextTestRunner(verbosity=1 if a.quiet else 2).run(unittest.TestSuite(tests))
    if a.fast and not result.failures and not result.errors:
        print("(browser tests skipped: run ./sentinel test for everything)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
