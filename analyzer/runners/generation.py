from __future__ import annotations

from pathlib import Path

from analyzer.generators.conftest_gen import generate_conftest
from analyzer.generators.page_objects import generate_page_objects
from analyzer.generators.tests import generate_tests
from analyzer.schema import DiscoveryResult


def run_generation(
    schema_path: str | Path | None = None,
    discovery: DiscoveryResult | None = None,
    output_dir: str | Path = "generated",
) -> list[Path]:
    """Generate test code from a discovery result or schema file.

    Provide either *discovery* (an in-memory object) or *schema_path*
    (path to a discovery JSON file).  Returns a list of all generated files.
    """
    output_dir = Path(output_dir)

    # Load discovery from file when not provided directly
    if discovery is None:
        if schema_path is None:
            print("Error: provide either --schema or a DiscoveryResult object")
            return []
        schema_path = Path(schema_path)
        if not schema_path.is_file():
            print(f"Error: schema file not found: {schema_path}")
            return []
        print(f"Loading discovery from {schema_path} ...")
        discovery = DiscoveryResult.from_json_file(schema_path)

    if not discovery.pages and not discovery.endpoints and not discovery.forms:
        print("Warning: discovery result is empty -- nothing to generate")
        return []

    print(f"Generating test code in {output_dir}/ ...")
    generated: list[Path] = []

    # Page objects
    po_files = generate_page_objects(discovery, output_dir)
    generated.extend(po_files)
    print(f"  Page objects: {len(po_files)} files")

    # Tests
    test_files = generate_tests(discovery, output_dir)
    generated.extend(test_files)
    print(f"  Tests:        {len(test_files)} files")

    # Conftest
    conftest_path = generate_conftest(discovery, output_dir)
    generated.append(conftest_path)
    print(f"  Conftest:     {conftest_path}")

    print(f"  Total:        {len(generated)} files generated")
    return generated
