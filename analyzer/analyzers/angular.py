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

# Angular route definition: { path: 'foo', component: FooComponent }
_ROUTE_OBJ_RE = re.compile(
    r"""\{\s*[^}]*?path\s*:\s*["']([^"']+)["'][^}]*?component\s*:\s*(\w+)""",
    re.DOTALL,
)

# Reversed: component before path
_ROUTE_OBJ_REV_RE = re.compile(
    r"""\{\s*[^}]*?component\s*:\s*(\w+)[^}]*?path\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

# Redirect route: { path: '', redirectTo: '/home' }
_REDIRECT_RE = re.compile(
    r"""\{\s*[^}]*?path\s*:\s*["']([^"']*)["'][^}]*?redirectTo\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

# Lazy loaded route: { path: 'foo', loadComponent: () => import('./foo/foo.component') }
_LAZY_ROUTE_RE = re.compile(
    r"""\{\s*[^}]*?path\s*:\s*["']([^"']+)["'][^}]*?loadComponent\s*:""",
    re.DOTALL,
)

# Form elements in Angular templates
_FORM_RE = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.DOTALL | re.IGNORECASE)
_INPUT_RE = re.compile(r"<input\b([^>]*)/?>", re.DOTALL | re.IGNORECASE)
_SELECT_RE = re.compile(r"<select\b([^>]*)>", re.DOTALL | re.IGNORECASE)
_TEXTAREA_RE = re.compile(r"<textarea\b([^>]*)>", re.DOTALL | re.IGNORECASE)

# Angular-specific bindings
_FORM_CONTROL_RE = re.compile(r"""formControlName\s*=\s*["'](\w+)["']""")
_NGMODEL_RE = re.compile(r"""\[\(ngModel\)\]\s*=\s*["']([^"']+)["']""")
_NGMODEL_ONEWAY_RE = re.compile(r"""\[ngModel\]\s*=\s*["']([^"']+)["']""")
_NGMODEL_BARE_RE = re.compile(r"""ngModel(?:\s|=)""")

# Submit button
_SUBMIT_BTN_RE = re.compile(
    r"""<button\b([^>]*)type\s*=\s*["']submit["']([^>]*)>([^<]*)</button>""",
    re.DOTALL | re.IGNORECASE,
)

# HTML attribute extraction (supports Angular binding syntax)
_ATTR_RE = re.compile(
    r"""([\w\[\]\(\).:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')"""
)


def _extract_attrs(attr_string: str) -> dict[str, str]:
    """Extract HTML/Angular attributes from an attribute string."""
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
    """Convert PascalCase component name to a human-readable name."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", component)
    return spaced.replace("Component", "").replace("Page", "").strip() or component


@register
class AngularAnalyzer(BaseAnalyzer):
    """Analyzer for Angular applications."""

    name: str = "angular"
    language: str = "typescript"

    def __init__(self, source_dir: str | Path) -> None:
        super().__init__(source_dir)
        self._frontend_dir: Path | None = None

    def detect(self) -> float:
        """Detect Angular by inspecting package.json and angular.json."""
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

        if "@angular/core" in all_deps:
            confidence = 0.7

        # Check for angular.json in root or frontend subdir
        frontend_root = found_pkg_path.parent if found_pkg_path else self.source_dir
        if (frontend_root / "angular.json").exists() or (self.source_dir / "angular.json").exists():
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
        """Discover pages from Angular routing modules and standalone route files."""
        pages: list[PageDefinition] = []
        seen_paths: set[str] = set()

        # Find routing module files
        routing_files = self._find_frontend_files("*-routing.module.ts") + self._find_frontend_files(
            "*routing.module.ts"
        )

        # Also check standalone route files (Angular 14+)
        roots = [self.source_dir]
        if self._frontend_dir:
            roots.insert(0, self._frontend_dir)
        for root in roots:
            for pattern in ("app.routes.ts", "src/app/app.routes.ts"):
                candidate = root / pattern
                if candidate.exists() and candidate not in routing_files:
                    routing_files.append(candidate)

        # Broader search for route definitions
        for fpath in self._find_frontend_files("*.routes.ts"):
            if fpath not in routing_files:
                routing_files.append(fpath)

        for fpath in routing_files:
            content = self.read_file(fpath)
            if not content:
                continue

            rel = self.relative_path(fpath)

            # Standard route objects: { path: 'foo', component: FooComponent }
            for m in _ROUTE_OBJ_RE.finditer(content):
                path_str, component = m.group(1), m.group(2)
                route_path = "/" + path_str.lstrip("/") if path_str else "/"
                if route_path not in seen_paths:
                    seen_paths.add(route_path)
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=route_path,
                            component=component,
                            source_file=rel,
                        )
                    )

            # Reversed attribute order
            for m in _ROUTE_OBJ_REV_RE.finditer(content):
                component, path_str = m.group(1), m.group(2)
                route_path = "/" + path_str.lstrip("/") if path_str else "/"
                if route_path not in seen_paths:
                    seen_paths.add(route_path)
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=route_path,
                            component=component,
                            source_file=rel,
                        )
                    )

            # Lazy loaded routes (path only, no component name available)
            for m in _LAZY_ROUTE_RE.finditer(content):
                path_str = m.group(1)
                route_path = "/" + path_str.lstrip("/") if path_str else "/"
                if route_path not in seen_paths:
                    seen_paths.add(route_path)
                    name = path_str.replace("-", " ").replace("/", " ").title().strip()
                    pages.append(
                        PageDefinition(
                            name=name or "Lazy Route",
                            path=route_path,
                            source_file=rel,
                        )
                    )

        return pages

    def analyze_endpoints(self) -> list:
        """Angular is a frontend framework -- no backend endpoints."""
        return []

    def analyze_models(self) -> list:
        """Angular is a frontend framework -- no data models."""
        return []

    def analyze_forms(self) -> list[FormDefinition]:
        """Parse Angular .html template files for form elements."""
        forms: list[FormDefinition] = []
        html_files = self._find_frontend_files("*.component.html") + self._find_frontend_files("*.html")
        seen_files: set[str] = set()

        for fpath in html_files:
            # Deduplicate
            fpath_str = str(fpath)
            if fpath_str in seen_files:
                continue
            seen_files.add(fpath_str)

            content = self.read_file(fpath)
            if not content or "<form" not in content.lower():
                continue

            rel = self.relative_path(fpath)

            for form_match in _FORM_RE.finditer(content):
                form_attrs_str = form_match.group(1)
                form_body = form_match.group(2)
                form_attrs = _extract_attrs(form_attrs_str)

                fields = self._extract_form_fields(form_body)
                test_id = form_attrs.get("data-testid", "")
                submit_btn = self._find_submit_button(form_body)

                # Detect reactive form group
                form_group = form_attrs.get("[formGroup]", "")

                form_name = (
                    test_id
                    or form_group
                    or form_attrs.get("name", "")
                    or form_attrs.get("id", "")
                    or f"form_{len(forms)}"
                )

                action = form_attrs.get("action", form_attrs.get("(ngSubmit)", ""))

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

    def _extract_form_fields(self, form_body: str) -> list[FormField]:
        """Extract form fields from Angular template HTML."""
        fields: list[FormField] = []
        seen_names: set[str] = set()

        # Standard <input> elements
        for m in _INPUT_RE.finditer(form_body):
            attr_str = m.group(1)
            attrs = _extract_attrs(attr_str)

            # Try formControlName first, then name, then ngModel
            name = ""
            fc_match = _FORM_CONTROL_RE.search(attr_str)
            if fc_match:
                name = fc_match.group(1)
            if not name:
                name = attrs.get("name", "")
            if not name:
                ng_match = _NGMODEL_RE.search(attr_str)
                if ng_match:
                    name = ng_match.group(1).split(".")[-1]
                else:
                    ng_match = _NGMODEL_ONEWAY_RE.search(attr_str)
                    if ng_match:
                        name = ng_match.group(1).split(".")[-1]

            if not name or name in seen_names:
                continue
            seen_names.add(name)

            fields.append(
                FormField(
                    name=name,
                    field_type=_field_type_from_str(attrs.get("type", "text")),
                    required="required" in attrs,
                    placeholder=attrs.get("placeholder", ""),
                    test_id=attrs.get("data-testid", ""),
                )
            )

        # <select> elements
        for m in _SELECT_RE.finditer(form_body):
            attr_str = m.group(1)
            attrs = _extract_attrs(attr_str)

            name = ""
            fc_match = _FORM_CONTROL_RE.search(attr_str)
            if fc_match:
                name = fc_match.group(1)
            if not name:
                name = attrs.get("name", "")

            if not name or name in seen_names:
                continue
            seen_names.add(name)

            fields.append(
                FormField(
                    name=name,
                    field_type=FieldType.SELECT,
                    required="required" in attrs,
                    test_id=attrs.get("data-testid", ""),
                )
            )

        # <textarea> elements
        for m in _TEXTAREA_RE.finditer(form_body):
            attr_str = m.group(1)
            attrs = _extract_attrs(attr_str)

            name = ""
            fc_match = _FORM_CONTROL_RE.search(attr_str)
            if fc_match:
                name = fc_match.group(1)
            if not name:
                name = attrs.get("name", "")

            if not name or name in seen_names:
                continue
            seen_names.add(name)

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
