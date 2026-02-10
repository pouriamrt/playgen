from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from analyzer.schema import (
    DiscoveryResult,
    EndpointDefinition,
    FieldType,
    FormDefinition,
    HttpMethod,
    ModelDefinition,
    PageDefinition,
)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _to_class_name(name: str) -> str:
    """Convert a name like ``user-profile`` to ``UserProfile``."""
    parts = re.split(r"[-_ /]+", name)
    return "".join(word.capitalize() for word in parts if word)


def _to_module_name(page_name: str) -> str:
    """Convert a page name to a module-safe filename."""
    name = re.sub(r"<[^>]+>", "", page_name)
    name = re.sub(r":[a-zA-Z_]\w*", "", name)
    name = re.sub(r"\{[^}]+\}", "", name)
    name = re.sub(r"[-/ ]+", "_", name.strip()).lower()
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "index"


def _page_object_module(page_name: str) -> str:
    """Return the import path for a generated page object."""
    return f"pages.{_to_module_name(page_name)}_page"


def _page_object_class(page_name: str) -> str:
    """Return the class name for a generated page object."""
    return _to_class_name(page_name) + "Page"


def _strip_chars(value: str, chars: str = "_") -> str:
    """Jinja2 custom filter: strip specific characters from both ends."""
    return value.strip(chars)


def _resolve_path_params(path: str) -> str:
    """Replace path parameter placeholders with sample values.

    ``{id}`` / ``{topic_id}`` / ``<int:pk>`` / ``:id`` → ``1``
    """
    resolved = re.sub(r"\{[^}]+\}", "1", path)
    resolved = re.sub(r"<[^>]+>", "1", resolved)
    resolved = re.sub(r":([a-zA-Z_]\w*)", "1", resolved)
    return resolved


def _jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["strip_chars"] = _strip_chars
    env.filters["resolve_params"] = _resolve_path_params
    return env


# ── Page render tests ────────────────────────────────────────────────────


def _generate_page_render_tests(
    discovery: DiscoveryResult,
    tests_dir: Path,
    env: Environment,
) -> list[Path]:
    """Generate a test file for each discovered page's render behaviour."""
    template = env.get_template("test_page_render.py.j2")
    generated: list[Path] = []

    for page in discovery.pages:
        class_name = _to_class_name(page.name)
        rendered = template.render(
            page=page,
            class_name=class_name,
            page_object_module=_page_object_module(page.name),
            page_object_class=_page_object_class(page.name),
        )

        filepath = tests_dir / f"test_{_to_module_name(page.name)}_render.py"
        filepath.write_text(rendered, encoding="utf-8")
        generated.append(filepath)

    return generated


# ── Form tests ───────────────────────────────────────────────────────────


def _generate_form_tests(
    discovery: DiscoveryResult,
    tests_dir: Path,
    env: Environment,
) -> list[Path]:
    """Generate test files for every form on every page."""
    template = env.get_template("test_form.py.j2")
    generated: list[Path] = []

    for page in discovery.pages:
        for form in page.forms:
            class_name = _to_class_name(form.name) + "Form"
            rendered = template.render(
                page=page,
                form=form,
                class_name=class_name,
                page_object_module=_page_object_module(page.name),
                page_object_class=_page_object_class(page.name),
            )

            form_module = _to_module_name(form.name)
            filepath = tests_dir / f"test_{form_module}_form.py"
            filepath.write_text(rendered, encoding="utf-8")
            generated.append(filepath)

    return generated


# ── API CRUD tests ───────────────────────────────────────────────────────


def _sample_payload(model: ModelDefinition | None) -> str:
    """Build a sample JSON payload dict as a string for the template."""
    if not model or not model.fields:
        return '{"name": "test"}'

    pairs: list[str] = []
    for field in model.fields:
        if field.primary_key:
            continue
        if field.field_type in (FieldType.EMAIL,):
            pairs.append(f'"{field.name}": "test@example.com"')
        elif field.field_type in (FieldType.PASSWORD,):
            pairs.append(f'"{field.name}": "SecurePass123!"')
        elif field.field_type in (FieldType.INTEGER, FieldType.NUMBER, FieldType.FLOAT):
            pairs.append(f'"{field.name}": 1')
        elif field.field_type in (FieldType.BOOLEAN,):
            pairs.append(f'"{field.name}": true')
        elif field.field_type in (FieldType.DATE,):
            pairs.append(f'"{field.name}": "2025-01-01"')
        elif field.field_type in (FieldType.DATETIME,):
            pairs.append(f'"{field.name}": "2025-01-01T00:00:00Z"')
        elif field.field_type in (FieldType.URL,):
            pairs.append(f'"{field.name}": "https://example.com"')
        else:
            pairs.append(f'"{field.name}": "test"')

    return "{" + ", ".join(pairs) + "}"


def _group_crud_endpoints(
    endpoints: list[EndpointDefinition],
) -> dict[str, dict[str, EndpointDefinition]]:
    """Group endpoints by resource base path into CRUD operations."""
    groups: dict[str, dict[str, EndpointDefinition]] = {}

    for ep in endpoints:
        # Normalise: /api/users/{id}/ -> /api/users
        base = re.sub(r"/\{[^}]+\}/?$", "", ep.path)
        base = re.sub(r"/:[a-zA-Z_]\w*/?$", "", base)
        base = re.sub(r"/<[^>]+>/?$", "", base)
        base = base.rstrip("/")

        if base not in groups:
            groups[base] = {}

        has_param = ep.path != base + "/" and ep.path != base

        if ep.method == HttpMethod.GET and not has_param:
            groups[base]["list"] = ep
        elif ep.method == HttpMethod.GET and has_param:
            groups[base]["read"] = ep
        elif ep.method == HttpMethod.POST:
            groups[base]["create"] = ep
        elif ep.method in (HttpMethod.PUT, HttpMethod.PATCH):
            groups[base]["update"] = ep
        elif ep.method == HttpMethod.DELETE:
            groups[base]["delete"] = ep

    return groups


def _find_model_for_endpoint(
    endpoint: EndpointDefinition,
    models: list[ModelDefinition],
) -> ModelDefinition | None:
    """Attempt to find a model matching an endpoint's request/response model."""
    for model in models:
        if model.name == endpoint.request_model or model.name == endpoint.response_model:
            return model
    return None


def _generate_api_tests(
    discovery: DiscoveryResult,
    tests_dir: Path,
    env: Environment,
) -> list[Path]:
    """Generate CRUD test files for grouped API endpoints."""
    template = env.get_template("test_api_crud.py.j2")
    generated: list[Path] = []

    groups = _group_crud_endpoints(discovery.endpoints)

    for base_path, ops in groups.items():
        # Derive a class name from the base path
        resource_name = base_path.rstrip("/").rsplit("/", 1)[-1]
        class_name = _to_class_name(resource_name)

        # Find a representative endpoint for model lookup
        representative = ops.get("create") or ops.get("list") or next(iter(ops.values()))
        model = None
        for ep in ops.values():
            model = _find_model_for_endpoint(ep, discovery.models)
            if model:
                break

        rendered = template.render(
            endpoint=representative,
            model=model,
            class_name=class_name,
            has_list="list" in ops,
            has_create="create" in ops,
            has_read="read" in ops,
            has_update="update" in ops,
            has_delete="delete" in ops,
            list_endpoint=ops.get("list"),
            create_endpoint=ops.get("create"),
            read_endpoint=ops.get("read"),
            update_endpoint=ops.get("update"),
            delete_endpoint=ops.get("delete"),
            sample_payload=_sample_payload(model),
        )

        module_name = _to_module_name(resource_name)
        filepath = tests_dir / f"test_{module_name}_api.py"
        filepath.write_text(rendered, encoding="utf-8")
        generated.append(filepath)

    return generated


# ── Navigation tests ─────────────────────────────────────────────────────


def _generate_navigation_tests(
    discovery: DiscoveryResult,
    tests_dir: Path,
    env: Environment,
) -> list[Path]:
    """Generate a single navigation test file covering all pages."""
    if not discovery.pages:
        return []

    template = env.get_template("test_navigation.py.j2")

    rendered = template.render(pages=discovery.pages)

    filepath = tests_dir / "test_navigation.py"
    filepath.write_text(rendered, encoding="utf-8")
    return [filepath]


# ── Public API ────────────────────────────────────────────────────────────


def generate_tests(
    discovery: DiscoveryResult,
    output_dir: Path,
) -> list[Path]:
    """Generate all test files from a discovery result.

    Returns a list of paths to the generated files.
    """
    tests_dir = output_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    env = _jinja_env()
    generated: list[Path] = []

    generated.extend(_generate_page_render_tests(discovery, tests_dir, env))
    generated.extend(_generate_form_tests(discovery, tests_dir, env))
    generated.extend(_generate_api_tests(discovery, tests_dir, env))
    generated.extend(_generate_navigation_tests(discovery, tests_dir, env))

    return generated
