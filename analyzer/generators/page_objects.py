from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from analyzer.schema import (
    DiscoveryResult,
    FormDefinition,
    InteractiveElement,
    PageDefinition,
)

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
    result = "".join(word.capitalize() for word in parts if word)
    return (result or "Index") + "Page"


def _to_module_name(page_name: str) -> str:
    """Convert a page name like ``user-profile`` to ``user_profile_page``."""
    name = re.sub(r"[-/ ]+", "_", _sanitize_name(page_name).strip()).lower()
    name = re.sub(r"_+", "_", name).strip("_")
    return f"{name or 'index'}_page"


def _selector_for_field(field_name: str, field_test_id: str, field_selector: str) -> tuple[str, str]:
    """Return (CONSTANT_NAME, selector_value) for a form field."""
    const = field_name.upper()
    if field_test_id:
        return const, f"[data-testid='{field_test_id}']"
    if field_selector:
        return const, field_selector
    return const, f"[name='{field_name}']"


def _build_selectors(page: PageDefinition) -> list[tuple[str, str]]:
    """Build a list of (CONSTANT_NAME, selector) tuples for the template."""
    selectors: list[tuple[str, str]] = []
    seen: set[str] = set()

    for form in page.forms:
        for field in form.fields:
            const, selector = _selector_for_field(field.name, field.test_id, field.selector)
            if const not in seen:
                selectors.append((const, selector))
                seen.add(const)

        # Submit button selector
        submit_const = f"{form.name.upper().replace('-', '_')}_SUBMIT"
        if form.submit_button:
            btn = form.submit_button
            if btn.test_id:
                submit_sel = f"[data-testid='{btn.test_id}']"
            elif btn.selector:
                submit_sel = btn.selector
            else:
                submit_sel = f"button[type='submit']"
        else:
            submit_sel = f"button[type='submit']"

        if submit_const not in seen:
            selectors.append((submit_const, submit_sel))
            seen.add(submit_const)

    for element in page.interactive_elements:
        text_const = element.text.upper().replace(" ", "_").replace("-", "_")
        if not text_const or text_const in seen:
            continue
        if element.test_id:
            sel = f"[data-testid='{element.test_id}']"
        elif element.selector:
            sel = element.selector
        else:
            continue
        selectors.append((text_const, sel))
        seen.add(text_const)

    return selectors


def generate_page_objects(
    discovery: DiscoveryResult,
    output_dir: Path,
) -> list[Path]:
    """Generate page object files from discovered pages.

    Returns a list of paths to the generated files.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("page_object.py.j2")

    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []

    for page in discovery.pages:
        # Skip SPA-detected pages without forms/test_ids (they get E2E tests)
        if not page.forms and not page.test_ids:
            continue

        class_name = _to_class_name(page.name)
        module_name = _to_module_name(page.name)
        selectors = _build_selectors(page)

        rendered = template.render(
            page=page,
            class_name=class_name,
            selectors=selectors,
        )

        filepath = pages_dir / f"{module_name}.py"
        filepath.write_text(rendered, encoding="utf-8")
        generated.append(filepath)

    return generated
