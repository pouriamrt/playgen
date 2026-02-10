#!/usr/bin/env python3
"""Environment setup script for the QA test suite.

Installs Python dependencies, Playwright browsers, and prepares
the environment for running tests.

Usage:
    python scripts/setup.py
    python scripts/setup.py --skip-browsers
    python scripts/setup.py --browsers chromium firefox
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QA Test Suite Environment Setup")
    parser.add_argument(
        "--skip-browsers",
        action="store_true",
        default=False,
        help="Skip Playwright browser installation",
    )
    parser.add_argument(
        "--browsers",
        nargs="+",
        choices=["chromium", "firefox", "webkit"],
        default=None,
        help="Specific browsers to install (default: all)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        default=False,
        help="Install development dependencies as well",
    )
    return parser.parse_args()


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and report success/failure."""
    print(f"\n{'>' * 3} {description}")
    print(f"    {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"    FAILED (exit code {result.returncode})")
        return False
    print(f"    OK")
    return True


def install_dependencies(dev: bool = False) -> bool:
    """Install Python dependencies from pyproject.toml."""
    cmd = [sys.executable, "-m", "pip", "install", "-e", "."]
    if dev:
        cmd = [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]
    return run_command(cmd, "Installing Python dependencies")


def install_playwright_browsers(browsers: list[str] | None = None) -> bool:
    """Install Playwright browsers."""
    cmd = [sys.executable, "-m", "playwright", "install"]
    if browsers:
        cmd.extend(browsers)
    else:
        # Install all browsers plus dependencies
        cmd.append("--with-deps")
    return run_command(cmd, "Installing Playwright browsers")


def create_env_file() -> None:
    """Create .env from .env.example if it doesn't exist."""
    env_path = PROJECT_ROOT / ".env"
    env_example_path = PROJECT_ROOT / ".env.example"

    if env_path.exists():
        print(f"\n{'>' * 3} .env file already exists, skipping")
        return

    if env_example_path.exists():
        shutil.copy2(env_example_path, env_path)
        print(f"\n{'>' * 3} Created .env from .env.example")
        print("    Please review and update .env with your settings")
    else:
        # Create a basic .env file
        env_content = """\
# QA Test Suite Configuration
# Copy this file to .env and update with your settings

# Application URLs
BASE_URL=http://localhost:3000
API_URL=http://localhost:3000/api

# Test credentials
ADMIN_USER=admin@example.com
ADMIN_PASS=admin123
TEST_USER=user@example.com
TEST_PASS=user123

# Database (optional - only needed for DB verification tests)
# DB_CONNECTION=postgresql://user:password@localhost:5432/testdb

# Browser settings
HEADLESS=true
SLOW_MO=0
VIEWPORT_WIDTH=1280
VIEWPORT_HEIGHT=720

# Artifact settings
SCREENSHOT_ON_FAILURE=true
VIDEO_RECORDING=off
TRACE_RECORDING=off

# Timeouts (milliseconds)
DEFAULT_TIMEOUT=10000
NAVIGATION_TIMEOUT=30000
"""
        env_path.write_text(env_content)
        # Also create the .env.example
        env_example_path.write_text(env_content)
        print(f"\n{'>' * 3} Created .env and .env.example files")
        print("    Please review and update .env with your settings")


def create_artifact_dirs() -> None:
    """Create artifact directories."""
    dirs = ["reports", "screenshots", "videos", "traces"]
    for d in dirs:
        dir_path = PROJECT_ROOT / d
        dir_path.mkdir(parents=True, exist_ok=True)
    print(f"\n{'>' * 3} Artifact directories created")


def verify_environment() -> None:
    """Verify the environment is properly set up."""
    print(f"\n{'=' * 50}")
    print("Environment Verification")
    print(f"{'=' * 50}")

    checks = []

    # Python version
    py_version = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 10)
    checks.append(("Python >= 3.10", py_ok, py_version))

    # pytest
    try:
        import pytest
        checks.append(("pytest", True, pytest.__version__))
    except ImportError:
        checks.append(("pytest", False, "not installed"))

    # playwright
    try:
        import playwright
        checks.append(("playwright", True, playwright.__version__))
    except ImportError:
        checks.append(("playwright", False, "not installed"))

    # faker
    try:
        import faker
        checks.append(("faker", True, faker.__version__))
    except ImportError:
        checks.append(("faker", False, "not installed"))

    # .env file
    env_exists = (PROJECT_ROOT / ".env").exists()
    checks.append((".env file", env_exists, "found" if env_exists else "missing"))

    # Print results
    all_ok = True
    for name, ok, detail in checks:
        status = "OK" if ok else "FAIL"
        print(f"  [{status:>4}] {name}: {detail}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("Environment is ready! Run tests with:")
        print("  python scripts/run_tests.py --suite smoke --browser chromium")
    else:
        print("Some checks failed. Please fix the issues above.")


def main() -> int:
    args = parse_args()

    print("QA Test Suite - Environment Setup")
    print(f"{'=' * 50}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Python:       {sys.version.split()[0]}")
    print(f"{'=' * 50}")

    # Step 1: Install dependencies
    if not install_dependencies(dev=args.dev):
        print("\nFailed to install dependencies. Aborting.")
        return 1

    # Step 2: Install Playwright browsers
    if not args.skip_browsers:
        if not install_playwright_browsers(args.browsers):
            print("\nFailed to install Playwright browsers.")
            print("You can retry with: python -m playwright install --with-deps")
    else:
        print(f"\n{'>' * 3} Skipping Playwright browser installation")

    # Step 3: Create .env file
    create_env_file()

    # Step 4: Create artifact directories
    create_artifact_dirs()

    # Step 5: Verify
    verify_environment()

    return 0


if __name__ == "__main__":
    sys.exit(main())
