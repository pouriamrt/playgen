from __future__ import annotations

import ast
import re
from pathlib import Path

from analyzer.analyzers.base import BaseAnalyzer
from analyzer.analyzers.registry import register
from analyzer.schema import (
    EndpointDefinition,
    FieldType,
    FormDefinition,
    FormField,
    HttpMethod,
    ModelDefinition,
    ModelField,
    PageDefinition,
)

_DJANGO_FIELD_MAP: dict[str, FieldType] = {
    "CharField": FieldType.STRING,
    "TextField": FieldType.TEXT,
    "IntegerField": FieldType.INTEGER,
    "SmallIntegerField": FieldType.INTEGER,
    "BigIntegerField": FieldType.INTEGER,
    "PositiveIntegerField": FieldType.INTEGER,
    "PositiveSmallIntegerField": FieldType.INTEGER,
    "PositiveBigIntegerField": FieldType.INTEGER,
    "FloatField": FieldType.FLOAT,
    "DecimalField": FieldType.FLOAT,
    "BooleanField": FieldType.BOOLEAN,
    "NullBooleanField": FieldType.BOOLEAN,
    "DateField": FieldType.DATE,
    "DateTimeField": FieldType.DATETIME,
    "TimeField": FieldType.DATETIME,
    "EmailField": FieldType.EMAIL,
    "URLField": FieldType.URL,
    "FileField": FieldType.FILE,
    "ImageField": FieldType.FILE,
    "ForeignKey": FieldType.FOREIGN_KEY,
    "OneToOneField": FieldType.FOREIGN_KEY,
    "JSONField": FieldType.JSON,
    "SlugField": FieldType.STRING,
    "UUIDField": FieldType.STRING,
    "AutoField": FieldType.INTEGER,
    "BigAutoField": FieldType.INTEGER,
}

_DJANGO_FORM_FIELD_MAP: dict[str, FieldType] = {
    "CharField": FieldType.STRING,
    "EmailField": FieldType.EMAIL,
    "URLField": FieldType.URL,
    "IntegerField": FieldType.INTEGER,
    "FloatField": FieldType.FLOAT,
    "DecimalField": FieldType.FLOAT,
    "BooleanField": FieldType.BOOLEAN,
    "DateField": FieldType.DATE,
    "DateTimeField": FieldType.DATETIME,
    "FileField": FieldType.FILE,
    "ImageField": FieldType.FILE,
    "ChoiceField": FieldType.SELECT,
    "TypedChoiceField": FieldType.SELECT,
    "MultipleChoiceField": FieldType.SELECT,
    "PasswordInput": FieldType.PASSWORD,
}

# HTTP methods that map to class-based view handler names
_CBV_METHOD_MAP: dict[str, HttpMethod] = {
    "get": HttpMethod.GET,
    "post": HttpMethod.POST,
    "put": HttpMethod.PUT,
    "patch": HttpMethod.PATCH,
    "delete": HttpMethod.DELETE,
    "head": HttpMethod.HEAD,
    "options": HttpMethod.OPTIONS,
}


def _get_string_value(node: ast.expr) -> str | None:
    """Extract a string value from an AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _get_keyword_value(call: ast.Call, keyword_name: str) -> ast.expr | None:
    """Get the value of a keyword argument from a Call node."""
    for kw in call.keywords:
        if kw.arg == keyword_name:
            return kw.value
    return None


def _get_int_keyword(call: ast.Call, keyword_name: str) -> int | None:
    """Get an integer keyword argument value."""
    val = _get_keyword_value(call, keyword_name)
    if val is not None and isinstance(val, ast.Constant) and isinstance(val.value, int):
        return val.value
    return None


def _get_bool_keyword(call: ast.Call, keyword_name: str) -> bool | None:
    """Get a boolean keyword argument value."""
    val = _get_keyword_value(call, keyword_name)
    if val is not None and isinstance(val, ast.Constant) and isinstance(val.value, bool):
        return val.value
    return None


def _get_func_name(node: ast.expr) -> str:
    """Get the function name from a call's func node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _inherits_from(class_node: ast.ClassDef, base_name: str) -> bool:
    """Check if a class inherits from a base with the given suffix."""
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base_name in base.id:
            return True
        if isinstance(base, ast.Attribute) and base_name in base.attr:
            return True
    return False


@register
class DjangoAnalyzer(BaseAnalyzer):
    """Analyzer for Django projects."""

    name: str = "django"
    language: str = "python"

    def detect(self) -> float:
        confidence = 0.0

        # Check for manage.py
        manage_files = self.find_files("manage.py")
        if manage_files:
            confidence += 0.4

        # Check for settings.py with INSTALLED_APPS
        settings_files = self.find_files("settings.py")
        for sf in settings_files:
            content = self.read_file(sf)
            if "INSTALLED_APPS" in content:
                confidence += 0.3
                break

        # Check for urls.py with urlpatterns
        urls_files = self.find_files("urls.py")
        for uf in urls_files:
            content = self.read_file(uf)
            if "urlpatterns" in content:
                confidence += 0.3
                break

        return min(confidence, 1.0)

    def analyze_endpoints(self) -> list[EndpointDefinition]:
        endpoints: list[EndpointDefinition] = []

        # Collect view info from views.py files first
        view_methods = self._collect_view_methods()

        # Parse urls.py files
        for urls_file in self.find_files("urls.py"):
            tree = self._parse_file(urls_file)
            if tree is None:
                continue
            rel = self.relative_path(urls_file)
            endpoints.extend(self._extract_url_patterns(tree, rel, view_methods))

        return endpoints

    def analyze_models(self) -> list[ModelDefinition]:
        models: list[ModelDefinition] = []

        for models_file in self.find_files("models.py"):
            tree = self._parse_file(models_file)
            if tree is None:
                continue
            rel = self.relative_path(models_file)

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if not _inherits_from(node, "Model"):
                    continue
                # Skip abstract mixin-style classes that don't directly use models.Model
                model_def = self._extract_model(node, rel)
                if model_def:
                    models.append(model_def)

        return models

    def analyze_pages(self) -> list[PageDefinition]:
        pages: list[PageDefinition] = []

        for urls_file in self.find_files("urls.py"):
            tree = self._parse_file(urls_file)
            if tree is None:
                continue
            rel = self.relative_path(urls_file)
            for pattern_info in self._find_url_paths(tree):
                path_str, view_name = pattern_info
                page_name = view_name or path_str.strip("/") or "index"
                pages.append(
                    PageDefinition(
                        name=page_name,
                        path="/" + path_str.lstrip("/") if path_str else "/",
                        source_file=rel,
                        requires_auth=False,
                    )
                )

        return pages

    def analyze_forms(self) -> list[FormDefinition]:
        forms: list[FormDefinition] = []

        for forms_file in self.find_files("forms.py"):
            tree = self._parse_file(forms_file)
            if tree is None:
                continue
            rel = self.relative_path(forms_file)

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                is_form = _inherits_from(node, "Form") or _inherits_from(
                    node, "ModelForm"
                )
                if not is_form:
                    continue
                form_def = self._extract_form(node, rel)
                if form_def:
                    forms.append(form_def)

        return forms

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_file(self, path: Path) -> ast.Module | None:
        source = self.read_file(path)
        if not source:
            return None
        try:
            return ast.parse(source, filename=str(path))
        except SyntaxError:
            return None

    def _find_url_paths(self, tree: ast.Module) -> list[tuple[str, str]]:
        """Return a list of (url_pattern, view_name) from a urls.py AST."""
        results: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = _get_func_name(node.func)
            if func_name not in ("path", "re_path", "url"):
                continue
            # First positional arg is the URL pattern
            if not node.args:
                continue
            url_str = _get_string_value(node.args[0])
            if url_str is None:
                continue
            # Second arg is the view
            view_name = ""
            if len(node.args) >= 2:
                view_name = self._resolve_view_name(node.args[1])
            # name keyword
            name_kw = _get_keyword_value(node, "name")
            if name_kw is not None:
                n = _get_string_value(name_kw)
                if n:
                    view_name = n
            results.append((url_str, view_name))
        return results

    @staticmethod
    def _resolve_view_name(node: ast.expr) -> str:
        """Try to extract a human-readable view name from the AST."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Call):
            # e.g. ViewClass.as_view()
            return _get_func_name(node.func)
        return ""

    def _collect_view_methods(self) -> dict[str, list[HttpMethod]]:
        """Scan views.py files and return {view_name: [methods]}."""
        view_methods: dict[str, list[HttpMethod]] = {}

        for views_file in self.find_files("views.py"):
            tree = self._parse_file(views_file)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                # Class-based views: look for get/post/put/delete methods
                methods: list[HttpMethod] = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m = _CBV_METHOD_MAP.get(item.name)
                        if m:
                            methods.append(m)
                if methods:
                    view_methods[node.name] = methods

                # Also register as_view name
                view_methods[node.name] = methods or [HttpMethod.GET]

        # Also scan function-based views
        for views_file in self.find_files("views.py"):
            tree = self._parse_file(views_file)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                # Skip methods inside classes (already handled)
                methods = self._detect_fbv_methods(node)
                if methods:
                    view_methods[node.name] = methods

        return view_methods

    @staticmethod
    def _detect_fbv_methods(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[HttpMethod]:
        """Detect HTTP methods used in a function-based view by inspecting
        `request.method == "GET"` style comparisons."""
        methods: list[HttpMethod] = []
        for node in ast.walk(func):
            if not isinstance(node, ast.Compare):
                continue
            # Looking for request.method == "X"
            left = node.left
            is_request_method = (
                isinstance(left, ast.Attribute)
                and left.attr == "method"
                and isinstance(left.value, ast.Name)
                and left.value.id == "request"
            )
            if not is_request_method:
                continue
            for comparator in node.comparators:
                val = _get_string_value(comparator)
                if val:
                    try:
                        methods.append(HttpMethod(val.upper()))
                    except ValueError:
                        pass
        return methods

    def _extract_url_patterns(
        self,
        tree: ast.Module,
        source_file: str,
        view_methods: dict[str, list[HttpMethod]],
    ) -> list[EndpointDefinition]:
        endpoints: list[EndpointDefinition] = []
        for url_pattern, view_name in self._find_url_paths(tree):
            # Determine path params from angle-bracket syntax: <type:name> or <name>
            path_params = re.findall(r"<(?:\w+:)?(\w+)>", url_pattern)
            # Determine HTTP methods from the view
            methods = view_methods.get(view_name, [HttpMethod.GET])
            for method in methods:
                endpoints.append(
                    EndpointDefinition(
                        path="/" + url_pattern.lstrip("/") if url_pattern else "/",
                        method=method,
                        name=view_name,
                        view_name=view_name,
                        source_file=source_file,
                        path_params=path_params,
                    )
                )
        return endpoints

    def _extract_model(self, class_node: ast.ClassDef, source_file: str) -> ModelDefinition | None:
        fields: list[ModelField] = []
        relationships: list[str] = []

        for stmt in class_node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            field_name = target.id

            if not isinstance(stmt.value, ast.Call):
                continue

            call = stmt.value
            func_name = _get_func_name(call.func)
            field_type = _DJANGO_FIELD_MAP.get(func_name, FieldType.UNKNOWN)

            max_length = _get_int_keyword(call, "max_length")
            unique = _get_bool_keyword(call, "unique") or False
            primary_key = _get_bool_keyword(call, "primary_key") or False

            # Determine required: default is True unless blank=True
            blank = _get_bool_keyword(call, "blank") or False
            null = _get_bool_keyword(call, "null") or False
            required = not (blank or null)

            # Default value
            default_val = None
            default_node = _get_keyword_value(call, "default")
            if default_node is not None and isinstance(default_node, ast.Constant):
                default_val = str(default_node.value)

            # Choices
            choices: list[str] = []
            choices_node = _get_keyword_value(call, "choices")
            if choices_node is not None:
                choices = self._extract_choices(choices_node)

            # Related model for ForeignKey / OneToOneField
            related_model = ""
            if func_name in ("ForeignKey", "OneToOneField", "ManyToManyField"):
                if call.args:
                    rm = _get_string_value(call.args[0])
                    if rm:
                        related_model = rm
                    elif isinstance(call.args[0], ast.Name):
                        related_model = call.args[0].id
                    elif isinstance(call.args[0], ast.Attribute):
                        related_model = call.args[0].attr
                if func_name == "ManyToManyField":
                    field_type = FieldType.FOREIGN_KEY
                relationships.append(related_model or field_name)

            fields.append(
                ModelField(
                    name=field_name,
                    field_type=field_type,
                    required=required,
                    unique=unique,
                    primary_key=primary_key,
                    max_length=max_length,
                    default=default_val,
                    choices=choices,
                    related_model=related_model,
                )
            )

        # Extract Meta.db_table if present
        table_name = ""
        for stmt in class_node.body:
            if isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
                for meta_stmt in stmt.body:
                    if isinstance(meta_stmt, ast.Assign):
                        for t in meta_stmt.targets:
                            if isinstance(t, ast.Name) and t.id == "db_table":
                                v = (
                                    _get_string_value(meta_stmt.value)
                                    if isinstance(meta_stmt.value, ast.Constant)
                                    else None
                                )
                                if v:
                                    table_name = v

        base_class = ""
        if class_node.bases:
            b = class_node.bases[0]
            if isinstance(b, ast.Attribute):
                base_class = f"{b.value.id}.{b.attr}" if isinstance(b.value, ast.Name) else b.attr
            elif isinstance(b, ast.Name):
                base_class = b.id

        return ModelDefinition(
            name=class_node.name,
            fields=fields,
            source_file=source_file,
            table_name=table_name,
            base_class=base_class,
            relationships=relationships,
        )

    @staticmethod
    def _extract_choices(node: ast.expr) -> list[str]:
        """Extract choice labels from a choices definition."""
        choices: list[str] = []
        if isinstance(node, (ast.List, ast.Tuple)):
            for elt in node.elts:
                if isinstance(elt, (ast.Tuple, ast.List)) and len(elt.elts) >= 2:
                    label = _get_string_value(elt.elts[0])
                    if label:
                        choices.append(label)
        return choices

    def _extract_form(self, class_node: ast.ClassDef, source_file: str) -> FormDefinition | None:
        fields: list[FormField] = []

        for stmt in class_node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue

            if not isinstance(stmt.value, ast.Call):
                continue

            call = stmt.value
            func_name = _get_func_name(call.func)
            field_type = _DJANGO_FORM_FIELD_MAP.get(func_name, FieldType.UNKNOWN)

            # Check required: default True unless required=False
            required_val = _get_bool_keyword(call, "required")
            required = required_val if required_val is not None else True

            label = ""
            label_node = _get_keyword_value(call, "label")
            if label_node is not None:
                label = _get_string_value(label_node) or ""

            fields.append(
                FormField(
                    name=target.id,
                    field_type=field_type,
                    required=required,
                    label=label,
                )
            )

        return FormDefinition(
            name=class_node.name,
            fields=fields,
            source_file=source_file,
        )
