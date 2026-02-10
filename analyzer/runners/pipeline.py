from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from analyzer.runners.discovery import run_discovery
from analyzer.runners.generation import run_generation


def run_pipeline(
    source_dir: str | Path,
    base_url: str = "http://localhost:3000",
    api_url: str | None = None,
    output_dir: str | Path = "generated",
    browser: str = "chromium",
    headed: bool = False,
    auto_run: bool = False,
) -> int:
    """Full pipeline: discover -> generate -> optionally run tests.

    Returns an exit code (0 = success).
    """
    output_dir = Path(output_dir)

    print("=" * 60)
    print("  Test Generation Pipeline")
    print("=" * 60)

    # Step 1 -- Discovery
    print("\n[Step 1/3] Discovery")
    discovery_path = output_dir / "discovery.json"
    discovery = run_discovery(source_dir, output_path=discovery_path)

    if not discovery.tech_stack:
        print("\nPipeline aborted: no frameworks detected.")
        return 1

    # Step 2 -- Generation
    print("\n[Step 2/3] Code Generation")
    generated = run_generation(discovery=discovery, output_dir=output_dir)

    if not generated:
        print("\nPipeline aborted: no files generated.")
        return 1

    # Step 3 -- Run tests (optional)
    if auto_run:
        import os

        print("\n[Step 3/3] Running Generated Tests")
        test_dir = output_dir / "tests"
        if not test_dir.is_dir():
            print(f"Error: test directory not found: {test_dir}")
            return 1

        env = os.environ.copy()
        env["BASE_URL"] = base_url
        if api_url:
            env["API_TEST_URL"] = api_url
        env["HEADLESS"] = "false" if headed else "true"

        cmd = [
            sys.executable, "-m", "pytest",
            str(test_dir),
            f"--base-url={base_url}",
            f"--browser={browser}",
            "-v",
            "--tb=short",
        ]
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env)
        return result.returncode
    else:
        print("\n[Step 3/3] Skipped (use --auto to run tests automatically)")
        api_hint = f" --api-url={api_url}" if api_url else ""
        print(f"\nTo run the generated tests manually:")
        print(f"  python -m pytest {output_dir / 'tests'} "
              f"--base-url={base_url}{api_hint} --browser={browser} -v")
        return 0
