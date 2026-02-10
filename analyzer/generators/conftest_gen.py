from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from analyzer.schema import DiscoveryResult, PageDefinition

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _sanitize_name(name: str) -> str:
    """Remove path parameter placeholders from a name."""
    name = re.sub(r"<[^>]+>", "", name)
    name = re.sub(r":[a-zA-Z_]\w*", "", name)
    name = re.sub(r"\{[^}]+\}", "", name)
    return name


def _to_class_name(page_name: str) -> str:
    """Convert a page name like ``user-profile`` to ``UserProfilePage``."""
    parts = re.split(r"[-_ /]+", _sanitize_name(page_name))
    return "".join(word.capitalize() for word in parts if word) + "Page"


def _to_module_name(page_name: str) -> str:
    """Convert a page name to a module-safe name."""
    name = re.sub(r"[-/ ]+", "_", _sanitize_name(page_name).strip()).lower()
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "index"


def _fixture_name(page_name: str) -> str:
    """Convert a page name to a pytest fixture name."""
    return f"{_to_module_name(page_name)}_page"


def generate_conftest(
    discovery: DiscoveryResult,
    output_dir: Path,
) -> Path:
    """Generate a conftest.py with fixtures for discovered pages.

    Returns the path to the generated file.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("conftest.py.j2")

    # Build import and fixture data for each page
    page_imports: list[tuple[str, str]] = []
    page_fixtures: list[tuple[str, str, bool]] = []

    for page in discovery.pages:
        # Skip SPA-detected pages without forms/test_ids (they get E2E tests)
        if not page.forms and not page.test_ids:
            continue

        module = f"pages.{_to_module_name(page.name)}_page"
        cls = _to_class_name(page.name)
        fixture = _fixture_name(page.name)

        page_imports.append((module, cls))
        page_fixtures.append((fixture, cls, page.requires_auth))

    rendered = template.render(
        page_imports=page_imports,
        page_fixtures=page_fixtures,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "conftest.py"
    filepath.write_text(rendered, encoding="utf-8")
    return filepath
