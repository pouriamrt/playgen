from __future__ import annotations

import json
import re
from pathlib import Path

from analyzer.analyzers.base import BaseAnalyzer
from analyzer.analyzers.registry import register
from analyzer.schema import (
    FieldType,
    FormDefinition,
    FormField,
    InteractiveElement,
    PageDefinition,
)

# Mapping of HTML input types to FieldType
_INPUT_TYPE_MAP: dict[str, FieldType] = {
    "text": FieldType.TEXT,
    "email": FieldType.EMAIL,
    "password": FieldType.PASSWORD,
    "number": FieldType.NUMBER,
    "date": FieldType.DATE,
    "datetime-local": FieldType.DATETIME,
    "file": FieldType.FILE,
    "checkbox": FieldType.CHECKBOX,
    "radio": FieldType.RADIO,
    "hidden": FieldType.HIDDEN,
    "url": FieldType.URL,
    "tel": FieldType.PHONE,
}

# Route object pattern: { path: '/foo', component: Bar } or { path: '/foo', name: 'bar', component: Bar }
_ROUTE_OBJ_RE = re.compile(
    r"""\{\s*[^}]*?path\s*:\s*["']([^"']+)["'][^}]*?component\s*:\s*(\w+)""",
    re.DOTALL,
)

# Reversed: component before path
_ROUTE_OBJ_REV_RE = re.compile(
    r"""\{\s*[^}]*?component\s*:\s*(\w+)[^}]*?path\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

# Route name extraction
_ROUTE_NAME_RE = re.compile(
    r"""\{\s*[^}]*?path\s*:\s*["']([^"']+)["'][^}]*?name\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

# <template> section of .vue files
_TEMPLATE_RE = re.compile(
    r"<template\b[^>]*>(.*?)</template>", re.DOTALL | re.IGNORECASE
)

# Form elements
_FORM_RE = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.DOTALL | re.IGNORECASE)
_INPUT_RE = re.compile(r"<input\b([^>]*)/?>", re.DOTALL | re.IGNORECASE)
_SELECT_RE = re.compile(r"<select\b([^>]*)>", re.DOTALL | re.IGNORECASE)
_TEXTAREA_RE = re.compile(r"<textarea\b([^>]*)>", re.DOTALL | re.IGNORECASE)

# v-model binding
_VMODEL_RE = re.compile(r"""v-model\s*=\s*["']([^"']+)["']""")

# Submit button
_SUBMIT_BTN_RE = re.compile(
    r"""<button\b([^>]*)type\s*=\s*["']submit["']([^>]*)>([^<]*)</button>""",
    re.DOTALL | re.IGNORECASE,
)

# HTML attribute extraction
_ATTR_RE = re.compile(r"""([\w:@.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def _extract_attrs(attr_string: str) -> dict[str, str]:
    """Extract HTML attributes from an attribute string."""
    attrs: dict[str, str] = {}
    for m in _ATTR_RE.finditer(attr_string):
        key = m.group(1)
        value = m.group(2) if m.group(2) is not None else (m.group(3) or "")
        attrs[key] = value
    if re.search(r"\brequired\b(?!\s*=)", attr_string):
        attrs["required"] = "true"
    return attrs


def _field_type_from_str(type_str: str) -> FieldType:
    """Map a string type to FieldType."""
    return _INPUT_TYPE_MAP.get(type_str.lower(), FieldType.TEXT)


def _component_to_name(component: str) -> str:
    """Convert a PascalCase component name to a human-readable name."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", component)
    return (
        spaced.replace("Page", "").replace("View", "").replace("Component", "").strip()
        or component
    )


@register
class VueAnalyzer(BaseAnalyzer):
    """Analyzer for Vue.js and Nuxt.js applications."""

    name: str = "vue"
    language: str = "javascript"

    def __init__(self, source_dir: str | Path) -> None:
        super().__init__(source_dir)
        self._frontend_dir: Path | None = None

    def detect(self) -> float:
        """Detect Vue/Nuxt by inspecting package.json dependencies."""
        confidence = 0.0

        # Look for package.json at root and common frontend subdirectories
        candidates = [self.source_dir / "package.json"]
        for subdir_name in ("frontend", "client", "web", "app", "ui"):
            candidates.append(self.source_dir / subdir_name / "package.json")

        data = None
        found_pkg_path: Path | None = None
        for pkg_path in candidates:
            if not pkg_path.exists():
                continue
            try:
                data = json.loads(self.read_file(pkg_path))
                found_pkg_path = pkg_path
                break
            except (json.JSONDecodeError, OSError):
                continue

        if data is None:
            return confidence

        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }

        if "vue" in all_deps:
            confidence = 0.5
        if "vue-router" in all_deps:
            confidence += 0.2
        if "nuxt" in all_deps or "nuxt3" in all_deps:
            confidence += 0.3

        if found_pkg_path and found_pkg_path.parent != self.source_dir:
            self._frontend_dir = found_pkg_path.parent

        return min(confidence, 1.0)

    def _find_frontend_files(self, pattern: str) -> list[Path]:
        """Find files, searching the frontend subdirectory first if detected."""
        results: list[Path] = []
        if self._frontend_dir:
            for path in self._frontend_dir.rglob(pattern):
                if not any(part in self._EXCLUDE_DIRS for part in path.parts):
                    results.append(path)
        if not results:
            results = self.find_files(pattern)
        return sorted(results)

    def analyze_pages(self) -> list[PageDefinition]:
        """Discover pages from Vue Router definitions and Nuxt file-based routing."""
        pages: list[PageDefinition] = []
        seen_paths: set[str] = set()

        # Scan for Vue Router route definitions
        self._scan_vue_router(pages, seen_paths)

        # Scan for Nuxt file-based routing
        self._scan_nuxt_pages(pages, seen_paths)

        return pages

    def analyze_endpoints(self) -> list:
        """Vue is a frontend framework -- no backend endpoints."""
        return []

    def analyze_models(self) -> list:
        """Vue is a frontend framework -- no data models."""
        return []

    def analyze_forms(self) -> list[FormDefinition]:
        """Parse <template> sections of .vue files for form elements."""
        forms: list[FormDefinition] = []
        vue_files = self._find_frontend_files("*.vue")

        for fpath in vue_files:
            content = self.read_file(fpath)
            if not content:
                continue

            # Extract template section
            template_match = _TEMPLATE_RE.search(content)
            if not template_match:
                continue

            template = template_match.group(1)
            rel = self.relative_path(fpath)

            for form_match in _FORM_RE.finditer(template):
                form_attrs_str = form_match.group(1)
                form_body = form_match.group(2)
                form_attrs = _extract_attrs(form_attrs_str)

                fields = self._extract_form_fields(form_body)
                action = form_attrs.get("action", form_attrs.get("@submit", ""))
                test_id = form_attrs.get("data-testid", "")
                submit_btn = self._find_submit_button(form_body)

                form_name = (
                    test_id
                    or form_attrs.get("name", "")
                    or form_attrs.get("id", "")
                    or f"form_{len(forms)}"
                )

                forms.append(
                    FormDefinition(
                        name=form_name,
                        action_url=action,
                        fields=fields,
                        submit_button=submit_btn,
                        source_file=rel,
                        test_id=test_id,
                    )
                )

        return forms

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _scan_vue_router(
        self, pages: list[PageDefinition], seen: set[str]
    ) -> None:
        """Scan router files for Vue Router route definitions."""
        router_patterns = [
            "router/index.js",
            "router/index.ts",
            "src/router/index.js",
            "src/router/index.ts",
            "src/router.js",
            "src/router.ts",
        ]

        # Also search any file matching *router*.js or *router*.ts
        router_files: list[Path] = []
        roots = [self.source_dir]
        if self._frontend_dir:
            roots.insert(0, self._frontend_dir)

        for root in roots:
            for pattern in router_patterns:
                candidate = root / pattern
                if candidate.exists() and candidate not in router_files:
                    router_files.append(candidate)

        # Broader search for route files
        for fpath in self._find_frontend_files("*router*.js") + self._find_frontend_files("*router*.ts"):
            if fpath not in router_files:
                router_files.append(fpath)

        # Build name lookup from _ROUTE_NAME_RE
        route_names: dict[str, str] = {}
        for fpath in router_files:
            content = self.read_file(fpath)
            if not content:
                continue
            for m in _ROUTE_NAME_RE.finditer(content):
                route_names[m.group(1)] = m.group(2)

        for fpath in router_files:
            content = self.read_file(fpath)
            if not content:
                continue

            rel = self.relative_path(fpath)

            # Match { path: '/x', component: Comp }
            for m in _ROUTE_OBJ_RE.finditer(content):
                path, component = m.group(1), m.group(2)
                if path not in seen:
                    seen.add(path)
                    name = route_names.get(path, _component_to_name(component))
                    pages.append(
                        PageDefinition(
                            name=name,
                            path=path,
                            component=component,
                            source_file=rel,
                        )
                    )

            # Reversed attribute order
            for m in _ROUTE_OBJ_REV_RE.finditer(content):
                component, path = m.group(1), m.group(2)
                if path not in seen:
                    seen.add(path)
                    name = route_names.get(path, _component_to_name(component))
                    pages.append(
                        PageDefinition(
                            name=name,
                            path=path,
                            component=component,
                            source_file=rel,
                        )
                    )

    def _scan_nuxt_pages(
        self, pages: list[PageDefinition], seen: set[str]
    ) -> None:
        """Scan Nuxt pages/ directory for file-based routes."""
        roots = [self.source_dir]
        if self._frontend_dir:
            roots.insert(0, self._frontend_dir)

        for root in roots:
            for pages_dir_name in ("pages", "src/pages"):
                pages_dir = root / pages_dir_name
                if pages_dir.is_dir():
                    self._collect_nuxt_file_routes(pages_dir, pages_dir, pages, seen)

    def _collect_nuxt_file_routes(
        self,
        base_dir: Path,
        current_dir: Path,
        pages: list[PageDefinition],
        seen: set[str],
    ) -> None:
        """Recursively collect routes from Nuxt pages/ directory."""
        try:
            entries = sorted(current_dir.iterdir())
        except OSError:
            return

        for entry in entries:
            if entry.name.startswith("_") or entry.name.startswith("."):
                continue
            if entry.is_dir():
                self._collect_nuxt_file_routes(base_dir, entry, pages, seen)
            elif entry.suffix == ".vue":
                rel_to_pages = entry.relative_to(base_dir)
                parts = list(rel_to_pages.parts)
                parts[-1] = entry.stem

                # Convert _param to :param (Nuxt 2) and [param] to :param (Nuxt 3)
                route_parts = []
                for part in parts:
                    if part.startswith("_"):
                        route_parts.append(f":{part[1:]}")
                    elif part.startswith("[") and part.endswith("]"):
                        route_parts.append(f":{part[1:-1]}")
                    else:
                        route_parts.append(part)

                if route_parts and route_parts[-1] == "index":
                    route_parts.pop()

                route_path = "/" + "/".join(route_parts) if route_parts else "/"

                if route_path not in seen:
                    seen.add(route_path)
                    component = entry.stem.capitalize()
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=route_path,
                            component=component,
                            source_file=self.relative_path(entry),
                        )
                    )

    def _extract_form_fields(self, form_body: str) -> list[FormField]:
        """Extract form fields including v-model bindings."""
        fields: list[FormField] = []

        for m in _INPUT_RE.finditer(form_body):
            attrs = _extract_attrs(m.group(1))
            # Use v-model as fallback name
            name = attrs.get("name", "")
            vmodel = attrs.get("v-model", "")
            if not name and vmodel:
                # Use last part of v-model path (e.g., "form.email" -> "email")
                name = vmodel.split(".")[-1]
            if not name:
                continue
            fields.append(
                FormField(
                    name=name,
                    field_type=_field_type_from_str(attrs.get("type", "text")),
                    required="required" in attrs,
                    placeholder=attrs.get("placeholder", ""),
                    test_id=attrs.get("data-testid", ""),
                )
            )

        for m in _SELECT_RE.finditer(form_body):
            attrs = _extract_attrs(m.group(1))
            name = attrs.get("name", "")
            vmodel = attrs.get("v-model", "")
            if not name and vmodel:
                name = vmodel.split(".")[-1]
            if not name:
                continue
            fields.append(
                FormField(
                    name=name,
                    field_type=FieldType.SELECT,
                    required="required" in attrs,
                    test_id=attrs.get("data-testid", ""),
                )
            )

        for m in _TEXTAREA_RE.finditer(form_body):
            attrs = _extract_attrs(m.group(1))
            name = attrs.get("name", "")
            vmodel = attrs.get("v-model", "")
            if not name and vmodel:
                name = vmodel.split(".")[-1]
            if not name:
                continue
            fields.append(
                FormField(
                    name=name,
                    field_type=FieldType.TEXTAREA,
                    required="required" in attrs,
                    test_id=attrs.get("data-testid", ""),
                )
            )

        return fields

    def _find_submit_button(self, form_body: str) -> InteractiveElement | None:
        """Find a submit button inside a form body."""
        m = _SUBMIT_BTN_RE.search(form_body)
        if m:
            before_attrs = m.group(1)
            after_attrs = m.group(2)
            text = m.group(3).strip()
            all_attrs = _extract_attrs(before_attrs + after_attrs)
            return InteractiveElement(
                element_type="button",
                text=text,
                test_id=all_attrs.get("data-testid", ""),
                action="submit",
            )
        return None
