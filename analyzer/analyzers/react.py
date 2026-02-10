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

# Regex for <Route path="..." component={...} /> (React Router v5)
_ROUTE_V5_RE = re.compile(
    r"""<Route\s[^>]*?path\s*=\s*["']([^"']+)["'][^>]*?component\s*=\s*\{(\w+)\}""",
    re.DOTALL,
)
# Regex for <Route path="..." element={<Component />} /> (React Router v6)
_ROUTE_V6_RE = re.compile(
    r"""<Route\s[^>]*?path\s*=\s*["']([^"']+)["'][^>]*?element\s*=\s*\{<(\w+)""",
    re.DOTALL,
)
# Also handle reversed attribute order
_ROUTE_V5_REV_RE = re.compile(
    r"""<Route\s[^>]*?component\s*=\s*\{(\w+)\}[^>]*?path\s*=\s*["']([^"']+)["']""",
    re.DOTALL,
)
_ROUTE_V6_REV_RE = re.compile(
    r"""<Route\s[^>]*?element\s*=\s*\{<(\w+)[^>]*?path\s*=\s*["']([^"']+)["']""",
    re.DOTALL,
)
# React Router v6.4+ createBrowserRouter([{ path: '/', element: <Comp /> }])
_CREATE_ROUTER_ROUTE_RE = re.compile(
    r"""\{\s*[^}]*?path\s*:\s*["']([^"']+)["'][^}]*?element\s*:\s*<(\w+)""",
    re.DOTALL,
)
# Reversed: element before path
_CREATE_ROUTER_ROUTE_REV_RE = re.compile(
    r"""\{\s*[^}]*?element\s*:\s*<(\w+)[^}]*?path\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

# Regex for <form ...>...</form> blocks
_FORM_RE = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.DOTALL | re.IGNORECASE)

# Regex for HTML input/select/textarea elements
_INPUT_RE = re.compile(r"<input\b([^>]*)/?>", re.DOTALL | re.IGNORECASE)
_SELECT_RE = re.compile(r"<select\b([^>]*)>", re.DOTALL | re.IGNORECASE)
_TEXTAREA_RE = re.compile(r"<textarea\b([^>]*)>", re.DOTALL | re.IGNORECASE)

# Formik <Field name="..." type="..." />
_FORMIK_FIELD_RE = re.compile(r"<Field\b([^>]*)/?>", re.DOTALL)

# react-hook-form register("fieldName") or register("fieldName", { ... })
_RHF_REGISTER_RE = re.compile(
    r"""register\(\s*["'](\w+)["']""",
)

# HTML attribute extraction
_ATTR_RE = re.compile(r"""(\w[\w-]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|\{([^}]*)\})""")

# Patterns for extracting interactive elements from JSX (SPA support)
_JSX_BUTTON_TEXT_RE = re.compile(
    r">\s*([A-Za-z][A-Za-z0-9 !?.]+?)\s*</button>",
    re.IGNORECASE,
)
_JSX_PLACEHOLDER_RE = re.compile(r'placeholder\s*=\s*"([^"]*)"')
_JSX_HEADING_RE = re.compile(
    r"<h([1-6])[^>]*>\s*([^<{]+?)\s*</h\1>",
    re.IGNORECASE,
)

# Submit button patterns
_SUBMIT_BTN_RE = re.compile(
    r"""<button\b([^>]*)type\s*=\s*["']submit["']([^>]*)>([^<]*)</button>""",
    re.DOTALL | re.IGNORECASE,
)


def _extract_attrs(attr_string: str) -> dict[str, str]:
    """Extract HTML/JSX attributes from an attribute string."""
    attrs: dict[str, str] = {}
    for m in _ATTR_RE.finditer(attr_string):
        key = m.group(1)
        value = m.group(2) or m.group(3) or m.group(4) or ""
        attrs[key] = value.strip()
    # Check for bare 'required' attribute (no value)
    if re.search(r"\brequired\b(?!\s*=)", attr_string):
        attrs["required"] = "true"
    return attrs


def _field_type_from_str(type_str: str) -> FieldType:
    """Map a string type to FieldType."""
    return _INPUT_TYPE_MAP.get(type_str.lower(), FieldType.TEXT)


def _component_to_name(component: str) -> str:
    """Convert a PascalCase component name to a human-readable name."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", component)
    return spaced.replace("Page", "").replace("Component", "").strip() or component


@register
class ReactAnalyzer(BaseAnalyzer):
    """Analyzer for React and Next.js applications."""

    name: str = "react"
    language: str = "javascript"

    def __init__(self, source_dir: str | Path) -> None:
        super().__init__(source_dir)
        # Set during detect() if package.json is found in a subdirectory
        self._frontend_dir: Path | None = None

    def detect(self) -> float:
        """Detect React/Next.js by inspecting package.json dependencies."""
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

        if "react" in all_deps:
            confidence = 0.5
        if "react-router-dom" in all_deps:
            confidence += 0.2
        if "next" in all_deps:
            confidence += 0.3

        # Remember the frontend directory if it's a subdirectory
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
        """Discover pages from React Router routes, Next.js routing, or SPA root."""
        pages: list[PageDefinition] = []
        seen_paths: set[str] = set()

        # Scan for React Router route definitions
        self._scan_router_routes(pages, seen_paths)

        # Scan for Next.js file-based routing
        self._scan_nextjs_pages(pages, seen_paths)

        # Fallback for SPAs without a router -- detect root App component
        if not pages:
            self._scan_spa_root(pages, seen_paths)

        return pages

    def analyze_endpoints(self) -> list:
        """React is a frontend framework -- no backend endpoints."""
        return []

    def analyze_models(self) -> list:
        """React is a frontend framework -- no data models."""
        return []

    def analyze_forms(self) -> list[FormDefinition]:
        """Scan JSX/TSX files for form elements."""
        forms: list[FormDefinition] = []
        files = self._find_frontend_files("*.jsx") + self._find_frontend_files("*.tsx")
        # Also scan .js/.ts files that may contain JSX
        files += self._find_frontend_files("*.js") + self._find_frontend_files("*.ts")
        seen: set[str] = set()

        for fpath in files:
            if fpath.suffix in (".js", ".ts"):
                # Skip non-JSX .js/.ts unless they contain JSX-like content
                content = self.read_file(fpath)
                if "<form" not in content.lower():
                    continue
            else:
                content = self.read_file(fpath)

            if not content:
                continue

            rel = self.relative_path(fpath)
            for form_match in _FORM_RE.finditer(content):
                form_attrs_str = form_match.group(1)
                form_body = form_match.group(2)
                form_attrs = _extract_attrs(form_attrs_str)

                form_key = f"{rel}:{form_match.start()}"
                if form_key in seen:
                    continue
                seen.add(form_key)

                fields = self._extract_form_fields(form_body)

                # Also detect react-hook-form register() calls
                for rhf_match in _RHF_REGISTER_RE.finditer(form_body):
                    field_name = rhf_match.group(1)
                    if not any(f.name == field_name for f in fields):
                        fields.append(
                            FormField(name=field_name, field_type=FieldType.TEXT)
                        )

                action = form_attrs.get("action", form_attrs.get("onSubmit", ""))
                method_str = form_attrs.get("method", "post").upper()
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
                        method=method_str if method_str in ("GET", "POST") else "POST",
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

    def _scan_router_routes(
        self, pages: list[PageDefinition], seen: set[str]
    ) -> None:
        """Scan JS/JSX/TS/TSX files for React Router <Route> definitions."""
        files = (
            self._find_frontend_files("*.jsx")
            + self._find_frontend_files("*.tsx")
            + self._find_frontend_files("*.js")
            + self._find_frontend_files("*.ts")
        )
        for fpath in files:
            content = self.read_file(fpath)
            if not content:
                continue
            has_route = "Route" in content
            has_create_router = "createBrowserRouter" in content or "createHashRouter" in content
            if not has_route and not has_create_router:
                continue

            rel = self.relative_path(fpath)

            # v5 style: <Route path="/x" component={Comp} />
            for m in _ROUTE_V5_RE.finditer(content):
                path, component = m.group(1), m.group(2)
                if path not in seen:
                    seen.add(path)
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=path,
                            component=component,
                            source_file=rel,
                        )
                    )

            # v5 reversed attribute order
            for m in _ROUTE_V5_REV_RE.finditer(content):
                component, path = m.group(1), m.group(2)
                if path not in seen:
                    seen.add(path)
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=path,
                            component=component,
                            source_file=rel,
                        )
                    )

            # v6 style: <Route path="/x" element={<Comp />} />
            for m in _ROUTE_V6_RE.finditer(content):
                path, component = m.group(1), m.group(2)
                if path not in seen:
                    seen.add(path)
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=path,
                            component=component,
                            source_file=rel,
                        )
                    )

            # v6 reversed
            for m in _ROUTE_V6_REV_RE.finditer(content):
                component, path = m.group(1), m.group(2)
                if path not in seen:
                    seen.add(path)
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=path,
                            component=component,
                            source_file=rel,
                        )
                    )

            # v6.4+ createBrowserRouter / createHashRouter object syntax
            for m in _CREATE_ROUTER_ROUTE_RE.finditer(content):
                path, component = m.group(1), m.group(2)
                if path not in seen:
                    seen.add(path)
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=path,
                            component=component,
                            source_file=rel,
                        )
                    )

            for m in _CREATE_ROUTER_ROUTE_REV_RE.finditer(content):
                component, path = m.group(1), m.group(2)
                if path not in seen:
                    seen.add(path)
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(component),
                            path=path,
                            component=component,
                            source_file=rel,
                        )
                    )

    def _scan_nextjs_pages(
        self, pages: list[PageDefinition], seen: set[str]
    ) -> None:
        """Scan Next.js pages/ or app/ directories for file-based routes."""
        # Search in both root and the detected frontend subdirectory
        roots = [self.source_dir]
        if self._frontend_dir:
            roots.insert(0, self._frontend_dir)

        for root in roots:
            # Next.js pages directory
            for pages_dir_name in ("pages", "src/pages"):
                pages_dir = root / pages_dir_name
                if pages_dir.is_dir():
                    self._collect_nextjs_file_routes(pages_dir, pages_dir, pages, seen)

            # Next.js app directory (App Router)
            for app_dir_name in ("app", "src/app"):
                app_dir = root / app_dir_name
                if app_dir.is_dir():
                    self._collect_nextjs_app_routes(app_dir, app_dir, pages, seen)

    def _collect_nextjs_file_routes(
        self,
        base_dir: Path,
        current_dir: Path,
        pages: list[PageDefinition],
        seen: set[str],
    ) -> None:
        """Recursively collect routes from Next.js pages/ directory."""
        try:
            entries = sorted(current_dir.iterdir())
        except OSError:
            return

        for entry in entries:
            if entry.name.startswith("_") or entry.name.startswith("."):
                continue
            if entry.is_dir():
                self._collect_nextjs_file_routes(base_dir, entry, pages, seen)
            elif entry.suffix in (".js", ".jsx", ".ts", ".tsx"):
                rel_to_pages = entry.relative_to(base_dir)
                parts = list(rel_to_pages.parts)
                # Remove extension from last part
                parts[-1] = entry.stem

                # Convert [param] to :param
                route_parts = []
                for part in parts:
                    if part.startswith("[") and part.endswith("]"):
                        route_parts.append(f":{part[1:-1]}")
                    else:
                        route_parts.append(part)

                # index files map to parent path
                if route_parts[-1] == "index":
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

    def _collect_nextjs_app_routes(
        self,
        base_dir: Path,
        current_dir: Path,
        pages: list[PageDefinition],
        seen: set[str],
    ) -> None:
        """Recursively collect routes from Next.js app/ directory (App Router)."""
        try:
            entries = sorted(current_dir.iterdir())
        except OSError:
            return

        for entry in entries:
            if entry.name.startswith("_") or entry.name.startswith("."):
                continue
            if entry.is_dir():
                self._collect_nextjs_app_routes(base_dir, entry, pages, seen)
            elif entry.stem == "page" and entry.suffix in (
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
            ):
                rel_to_app = entry.parent.relative_to(base_dir)
                parts = list(rel_to_app.parts)

                route_parts = []
                for part in parts:
                    if part.startswith("[") and part.endswith("]"):
                        route_parts.append(f":{part[1:-1]}")
                    elif part == ".":
                        continue
                    else:
                        route_parts.append(part)

                route_path = "/" + "/".join(route_parts) if route_parts else "/"

                if route_path not in seen:
                    seen.add(route_path)
                    dir_name = entry.parent.name if entry.parent != base_dir else "Home"
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(dir_name),
                            path=route_path,
                            component=dir_name,
                            source_file=self.relative_path(entry),
                        )
                    )

    def _extract_form_fields(self, form_body: str) -> list[FormField]:
        """Extract form fields from HTML/JSX form body."""
        fields: list[FormField] = []

        # Standard <input> elements
        for m in _INPUT_RE.finditer(form_body):
            attrs = _extract_attrs(m.group(1))
            name = attrs.get("name", "")
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

        # <select> elements
        for m in _SELECT_RE.finditer(form_body):
            attrs = _extract_attrs(m.group(1))
            name = attrs.get("name", "")
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

        # <textarea> elements
        for m in _TEXTAREA_RE.finditer(form_body):
            attrs = _extract_attrs(m.group(1))
            name = attrs.get("name", "")
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

        # Formik <Field> elements
        for m in _FORMIK_FIELD_RE.finditer(form_body):
            attrs = _extract_attrs(m.group(1))
            name = attrs.get("name", "")
            if not name or any(f.name == name for f in fields):
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

    # ------------------------------------------------------------------
    # SPA (single-page app without router) helpers
    # ------------------------------------------------------------------

    def _scan_spa_root(
        self, pages: list[PageDefinition], seen: set[str]
    ) -> None:
        """For SPAs without a router, find the App component as the root page."""
        app_files: list[Path] = []
        for pattern in ("App.jsx", "App.tsx"):
            app_files.extend(self._find_frontend_files(pattern))

        if not app_files:
            return

        app_file = app_files[0]
        content = self.read_file(app_file)
        if not content:
            return

        rel = self.relative_path(app_file)

        # Extract interactive elements (buttons, inputs)
        elements = self._extract_jsx_interactive_elements(content)

        # Extract heading text for title
        headings = self._extract_jsx_headings(content)
        title = headings[0] if headings else ""

        if "/" not in seen:
            seen.add("/")
            pages.append(
                PageDefinition(
                    name="App",
                    path="/",
                    title=title,
                    component="App",
                    source_file=rel,
                    interactive_elements=elements,
                )
            )

    def _extract_jsx_interactive_elements(
        self, content: str
    ) -> list[InteractiveElement]:
        """Extract buttons and inputs from JSX, even outside <form> tags."""
        elements: list[InteractiveElement] = []
        seen_text: set[str] = set()

        # Buttons with static text
        for m in _JSX_BUTTON_TEXT_RE.finditer(content):
            text = m.group(1).strip()
            if text and text not in seen_text:
                seen_text.add(text)
                elements.append(
                    InteractiveElement(
                        element_type="button",
                        text=text,
                        action="click",
                    )
                )

        # Inputs with placeholder
        for m in _JSX_PLACEHOLDER_RE.finditer(content):
            placeholder = m.group(1).strip()
            if placeholder and placeholder not in seen_text:
                seen_text.add(placeholder)
                elements.append(
                    InteractiveElement(
                        element_type="input",
                        text=placeholder,
                    )
                )

        return elements

    def _extract_jsx_headings(self, content: str) -> list[str]:
        """Extract static heading text from JSX."""
        headings: list[str] = []
        for m in _JSX_HEADING_RE.finditer(content):
            text = m.group(2).strip()
            if text and text not in headings:
                headings.append(text)
        return headings
