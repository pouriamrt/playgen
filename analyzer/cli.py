from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="analyzer",
        description="Dynamic code-aware test generator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- discover -----------------------------------------------------------
    discover_parser = subparsers.add_parser(
        "discover",
        help="Analyze source code and produce discovery.json",
    )
    discover_parser.add_argument(
        "source_dir",
        help="Path to the application source code",
    )
    discover_parser.add_argument(
        "--output", "-o",
        default="generated/discovery.json",
        help="Output path for discovery JSON (default: generated/discovery.json)",
    )

    # --- generate -----------------------------------------------------------
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate test code from discovery data",
    )
    gen_parser.add_argument(
        "--schema", "-s",
        default="generated/discovery.json",
        help="Path to discovery.json (default: generated/discovery.json)",
    )
    gen_parser.add_argument(
        "--output-dir", "-o",
        default="generated",
        help="Output directory for generated code (default: generated)",
    )

    # --- run ----------------------------------------------------------------
    run_parser = subparsers.add_parser(
        "run",
        help="Run generated tests",
    )
    run_parser.add_argument(
        "--base-url",
        default="http://localhost:3000",
        help="Base URL for browser tests (default: http://localhost:3000)",
    )
    run_parser.add_argument(
        "--api-url",
        default=None,
        help="Base URL for API tests (defaults to --base-url)",
    )
    run_parser.add_argument(
        "--browser",
        default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Browser to use (default: chromium)",
    )
    run_parser.add_argument(
        "--test-dir",
        default="generated/tests",
        help="Directory containing generated tests (default: generated/tests)",
    )

    # --- pipeline -----------------------------------------------------------
    pipe_parser = subparsers.add_parser(
        "pipeline",
        help="Full pipeline: discover -> generate -> run",
    )
    pipe_parser.add_argument(
        "source_dir",
        help="Path to the application source code",
    )
    pipe_parser.add_argument(
        "--base-url",
        default="http://localhost:3000",
        help="Base URL for browser tests (default: http://localhost:3000)",
    )
    pipe_parser.add_argument(
        "--api-url",
        default=None,
        help="Base URL for API tests (defaults to --base-url)",
    )
    pipe_parser.add_argument(
        "--output-dir",
        default="generated",
        help="Output directory (default: generated)",
    )
    pipe_parser.add_argument(
        "--browser",
        default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Browser to use (default: chromium)",
    )
    pipe_parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically run tests after generation",
    )

    args = parser.parse_args()
    _dispatch(args)


def _dispatch(args: argparse.Namespace) -> None:
    """Route parsed arguments to the appropriate runner."""
    if args.command == "discover":
        from analyzer.runners.discovery import run_discovery

        run_discovery(args.source_dir, output_path=args.output)

    elif args.command == "generate":
        from analyzer.runners.generation import run_generation

        run_generation(schema_path=args.schema, output_dir=args.output_dir)

    elif args.command == "run":
        test_dir = Path(args.test_dir)
        if not test_dir.is_dir():
            print(f"Error: test directory not found: {test_dir}")
            sys.exit(1)

        import os

        env = os.environ.copy()
        if args.api_url:
            env["API_TEST_URL"] = args.api_url

        cmd = [
            sys.executable, "-m", "pytest",
            str(test_dir),
            f"--base-url={args.base_url}",
            f"--browser={args.browser}",
            "-v",
            "--tb=short",
        ]
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)

    elif args.command == "pipeline":
        from analyzer.runners.pipeline import run_pipeline

        code = run_pipeline(
            source_dir=args.source_dir,
            base_url=args.base_url,
            api_url=args.api_url,
            output_dir=args.output_dir,
            browser=args.browser,
            auto_run=args.auto,
        )
        sys.exit(code)


if __name__ == "__main__":
    main()
