#!/usr/bin/env python3
"""Main test runner script for the QA test suite.

Provides a CLI interface to run tests with various configurations
including suite selection, browser choice, parallelism, and reporting.

Usage:
    python scripts/run_tests.py --suite smoke --browser chromium --headed
    python scripts/run_tests.py --suite regression --browser all --workers 4
    python scripts/run_tests.py --suite full --base-url https://staging.example.com
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SUITE_MARKERS = {
    "smoke": "smoke",
    "regression": "regression",
    "auth": "auth",
    "forms": "forms",
    "crud": "crud",
    "navigation": "navigation",
    "api": "api",
    "performance": "performance",
    "accessibility": "accessibility",
    "critical": "critical",
    "full": "",
}

BROWSERS = ("chromium", "firefox", "webkit")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="QA Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --suite smoke --browser chromium
  %(prog)s --suite regression --browser all --workers 4
  %(prog)s --suite full --headed --base-url https://staging.example.com
  %(prog)s --suite auth --browser firefox --report allure
        """,
    )

    parser.add_argument(
        "--suite",
        choices=list(SUITE_MARKERS.keys()),
        default="smoke",
        help="Test suite to run (default: smoke)",
    )
    parser.add_argument(
        "--browser",
        choices=[*BROWSERS, "all"],
        default="chromium",
        help="Browser to use (default: chromium)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=False,
        help="Run browser in headed mode (default: headless)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1). Use 'auto' for CPU count.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Override the base URL for tests",
    )
    parser.add_argument(
        "--report",
        choices=["html", "allure", "both"],
        default="html",
        help="Report format (default: html)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Default test timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="Number of retries for failed tests (default: 0)",
    )
    parser.add_argument(
        "--tracing",
        action="store_true",
        default=False,
        help="Enable Playwright trace recording on failure",
    )
    parser.add_argument(
        "--video",
        action="store_true",
        default=False,
        help="Enable video recording",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Verbose output",
    )
    parser.add_argument(
        "-k",
        type=str,
        default=None,
        metavar="EXPRESSION",
        help="Only run tests matching the given substring expression (pytest -k)",
    )
    parser.add_argument(
        "--generated",
        action="store_true",
        default=False,
        help="Also include generated tests from generated/tests/",
    )

    return parser.parse_args()


def check_playwright_browsers() -> bool:
    """Check if Playwright browsers are installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        # --dry-run may not be supported; check if the binary exists instead
        playwright_dir = Path.home() / ".cache" / "ms-playwright"
        if not playwright_dir.exists():
            # Also check Windows-style path
            playwright_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
        return playwright_dir.exists() and any(playwright_dir.iterdir())


def validate_environment() -> list[str]:
    """Validate the environment is ready for running tests."""
    issues = []

    # Check Python packages
    try:
        import playwright  # noqa: F401
    except ImportError:
        issues.append("playwright is not installed. Run: pip install -e .[dev]")

    try:
        import pytest  # noqa: F401
    except ImportError:
        issues.append("pytest is not installed. Run: pip install -e .[dev]")

    # Check .env file
    env_path = PROJECT_ROOT / ".env"
    env_example_path = PROJECT_ROOT / ".env.example"
    if not env_path.exists() and env_example_path.exists():
        issues.append(
            ".env file not found. Copy .env.example to .env and configure it."
        )

    return issues


def build_pytest_command(args: argparse.Namespace) -> list[str]:
    """Build the pytest command line from parsed arguments."""
    cmd = [sys.executable, "-m", "pytest"]

    # Test directory
    cmd.append(str(PROJECT_ROOT / "tests"))

    # Include generated tests when requested
    if args.generated:
        generated_tests = PROJECT_ROOT / "generated" / "tests"
        if generated_tests.is_dir():
            cmd.append(str(generated_tests))
        else:
            print(f"Warning: generated test directory not found: {generated_tests}")

    # Suite marker
    marker = SUITE_MARKERS.get(args.suite, "")
    if marker:
        cmd.extend(["-m", marker])

    # Browser selection
    if args.browser == "all":
        # Run with all browsers via parameterization
        browsers = ",".join(BROWSERS)
        cmd.extend(["--browser", "chromium", "--browser", "firefox", "--browser", "webkit"])
    else:
        cmd.extend(["--browser", args.browser])

    # Headed/headless
    if args.headed:
        cmd.append("--headed")

    # Parallel workers
    if args.workers > 1:
        cmd.extend(["-n", str(args.workers)])

    # Timeout
    cmd.extend(["--timeout", str(args.timeout)])

    # Retries
    if args.retries > 0:
        cmd.extend(["--retries", str(args.retries)])

    # Reports
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if args.report in ("html", "both"):
        cmd.extend([
            "--html", str(reports_dir / "report.html"),
            "--self-contained-html",
        ])

    if args.report in ("allure", "both"):
        allure_dir = reports_dir / "allure-results"
        allure_dir.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--alluredir", str(allure_dir)])

    # Verbose
    if args.verbose:
        cmd.append("-v")

    # Filter expression
    if args.k:
        cmd.extend(["-k", args.k])

    # Strict markers
    cmd.append("--strict-markers")
    cmd.append("--tb=short")

    return cmd


def build_env(args: argparse.Namespace) -> dict[str, str]:
    """Build environment variables for the test run."""
    env = os.environ.copy()

    if args.base_url:
        env["BASE_URL"] = args.base_url

    env["HEADLESS"] = "false" if args.headed else "true"

    if args.tracing:
        env["TRACE_RECORDING"] = "on"

    if args.video:
        env["VIDEO_RECORDING"] = "on"

    return env


def main() -> int:
    args = parse_args()

    print(f"QA Test Suite Runner")
    print(f"{'=' * 50}")
    print(f"Suite:    {args.suite}")
    print(f"Browser:  {args.browser}")
    print(f"Mode:     {'headed' if args.headed else 'headless'}")
    print(f"Workers:  {args.workers}")
    print(f"Report:   {args.report}")
    print(f"{'=' * 50}")
    print()

    # Validate environment
    issues = validate_environment()
    if issues:
        print("Environment issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("Run 'python scripts/setup.py' to set up the environment.")
        return 1

    # Check Playwright browsers
    if not check_playwright_browsers():
        print("Playwright browsers may not be installed.")
        print("Run: python -m playwright install")
        print()

    # Build and execute the command
    cmd = build_pytest_command(args)
    env = build_env(args)

    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, env=env, cwd=str(PROJECT_ROOT))

    # Post-run summary
    print()
    print(f"{'=' * 50}")
    print(f"Exit code: {result.returncode}")
    if result.returncode == 0:
        print("All tests passed!")
    else:
        print("Some tests failed. Check the report for details.")

    reports_dir = PROJECT_ROOT / "reports"
    html_report = reports_dir / "report.html"
    if html_report.exists():
        print(f"HTML Report: {html_report}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
