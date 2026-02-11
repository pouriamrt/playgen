from __future__ import annotations

import ast
import re
from pathlib import Path

from analyzer.analyzers.base import BaseAnalyzer
from analyzer.analyzers.registry import register
from analyzer.schema import (
    EndpointDefinition,
    FieldType,
    HttpMethod,
    ModelDefinition,
    ModelField,
    PageDefinition,
)

_SQLALCHEMY_TYPE_MAP: dict[str, FieldType] = {
    "String": FieldType.STRING,
    "Text": FieldType.TEXT,
    "Integer": FieldType.INTEGER,
    "SmallInteger": FieldType.INTEGER,
    "BigInteger": FieldType.INTEGER,
    "Float": FieldType.FLOAT,
    "Numeric": FieldType.FLOAT,
    "Boolean": FieldType.BOOLEAN,
    "Date": FieldType.DATE,
    "DateTime": FieldType.DATETIME,
    "Time": FieldType.DATETIME,
    "LargeBinary": FieldType.FILE,
    "JSON": FieldType.JSON,
    "Enum": FieldType.SELECT,
}

_METHOD_STR_MAP: dict[str, HttpMethod] = {
    "GET": HttpMethod.GET,
    "POST": HttpMethod.POST,
    "PUT": HttpMethod.PUT,
    "PATCH": HttpMethod.PATCH,
    "DELETE": HttpMethod.DELETE,
    "OPTIONS": HttpMethod.OPTIONS,
    "HEAD": HttpMethod.HEAD,
}

# Patterns that suggest an API route rather than an HTML page
_API_PATH_PREFIXES = ("/api/", "/api", "/v1/", "/v2/", "/v3/")


def _get_string_value(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _get_func_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _get_keyword_value(call: ast.Call, keyword_name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == keyword_name:
            return kw.value
    return None


def _get_bool_keyword(call: ast.Call, keyword_name: str) -> bool | None:
    val = _get_keyword_value(call, keyword_name)
    if val is not None and isinstance(val, ast.Constant) and isinstance(val.value, bool):
        return val.value
    return None


def _get_int_keyword(call: ast.Call, keyword_name: str) -> int | None:
    val = _get_keyword_value(call, keyword_name)
    if val is not None and isinstance(val, ast.Constant) and isinstance(val.value, int):
        return val.value
    return None


@register
class FlaskAnalyzer(BaseAnalyzer):
    """Analyzer for Flask projects."""

    name: str = "flask"
    language: str = "python"

    def detect(self) -> float:
        confidence = 0.0

        # Check for flask imports in .py files
        import_found = False
        for py_file in self.find_files("*.py"):
            tree = self._parse_file(py_file)
            if tree is None:
                continue
            if self._has_flask_import(tree):
                import_found = True
                break

        if import_found:
            confidence += 0.5

        # Check dependency files
        if self._check_dependency_files("flask"):
            confidence += 0.3

        # Check for Flask() instantiation
        for py_file in self.find_files("*.py"):
            tree = self._parse_file(py_file)
            if tree is None:
                continue
            if self._has_flask_app(tree):
                confidence += 0.2
                break

        return min(confidence, 1.0)

    def analyze_endpoints(self) -> list[EndpointDefinition]:
        endpoints: list[EndpointDefinition] = []

        for py_file in self.find_files("*.py"):
            tree = self._parse_file(py_file)
            if tree is None:
                continue
            rel = self.relative_path(py_file)
            prefix = self._find_blueprint_prefix(tree)
            endpoints.extend(self._extract_endpoints(tree, rel, prefix))

        return endpoints

    def analyze_models(self) -> list[ModelDefinition]:
        models: list[ModelDefinition] = []

        for py_file in self.find_files("*.py"):
            tree = self._parse_file(py_file)
            if tree is None:
                continue
            rel = self.relative_path(py_file)

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if not self._inherits_from_db_model(node):
                    continue
                model_def = self._extract_model(node, rel)
                if model_def:
                    models.append(model_def)

        return models

    def analyze_pages(self) -> list[PageDefinition]:
        """Return pages for routes that likely serve HTML (non-API routes)."""
        pages: list[PageDefinition] = []

        for py_file in self.find_files("*.py"):
            tree = self._parse_file(py_file)
            if tree is None:
                continue
            rel = self.relative_path(py_file)
            bp_prefix = self._find_blueprint_prefix(tree)

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                route_info = self._get_route_info_from_decorators(node)
                if route_info is None:
                    continue

                path_str, _methods = route_info

                # Prepend the blueprint url_prefix
                if bp_prefix:
                    path_str = bp_prefix.rstrip("/") + "/" + path_str.lstrip("/")
                    path_str = "/" + path_str.lstrip("/")

                # Skip routes that look like API endpoints
                if any(path_str.startswith(pfx) for pfx in _API_PATH_PREFIXES):
                    continue

                # Also skip if the function body contains jsonify calls (API-like)
                if self._returns_json(node):
                    continue

                page_name = node.name
                pages.append(
                    PageDefinition(
                        name=page_name,
                        path=path_str,
                        source_file=rel,
                    )
                )

        return pages

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

    @staticmethod
    def _has_flask_import(tree: ast.Module) -> bool:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "flask" or alias.name.startswith("flask."):
                        return True
            if isinstance(node, ast.ImportFrom):
                if node.module and (
                    node.module == "flask" or node.module.startswith("flask.")
                ):
                    return True
        return False

    @staticmethod
    def _has_flask_app(tree: ast.Module) -> bool:
        """Check for `Flask(__name__)` or similar instantiation."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _get_func_name(node.func) == "Flask":
                return True
        return False

    def _check_dependency_files(self, package_name: str) -> bool:
        for req_file in self.find_files("requirements*.txt"):
            content = self.read_file(req_file)
            if package_name in content.lower():
                return True
        for toml_file in self.find_files("pyproject.toml"):
            content = self.read_file(toml_file)
            if package_name in content.lower():
                return True
        return False

    def _extract_endpoints(
        self, tree: ast.Module, source_file: str, prefix: str = ""
    ) -> list[EndpointDefinition]:
        endpoints: list[EndpointDefinition] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            route_info = self._get_route_info_from_decorators(node)
            if route_info is None:
                continue

            path_str, methods = route_info
            func_name = node.name

            # Prepend the blueprint url_prefix
            if prefix:
                path_str = prefix.rstrip("/") + "/" + path_str.lstrip("/")
                path_str = "/" + path_str.lstrip("/")

            # Extract path parameters from <converter:name> or <name> syntax
            path_params = re.findall(r"<(?:\w+:)?(\w+)>", path_str)

            for method in methods:
                endpoints.append(
                    EndpointDefinition(
                        path=path_str,
                        method=method,
                        name=func_name,
                        view_name=func_name,
                        source_file=source_file,
                        path_params=path_params,
                    )
                )

        return endpoints

    @staticmethod
    def _find_blueprint_prefix(tree: ast.Module) -> str:
        """Find Blueprint(..., url_prefix="/...") defined in the file."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _get_func_name(node.func) != "Blueprint":
                continue
            val = _get_keyword_value(node, "url_prefix")
            if val is not None:
                prefix = _get_string_value(val)
                if prefix:
                    return prefix
        return ""

    @staticmethod
    def _get_route_info_from_decorators(
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> tuple[str, list[HttpMethod]] | None:
        """Extract (path, methods) from @app.route or @blueprint.route decorators."""
        for decorator in func_node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue

            attr_name = decorator.func.attr
            if attr_name != "route":
                continue

            # First positional arg is the path
            if not decorator.args:
                continue
            path_str = _get_string_value(decorator.args[0])
            if path_str is None:
                continue

            # methods keyword
            methods_list: list[HttpMethod] = []
            methods_node = _get_keyword_value(decorator, "methods")
            if methods_node is not None and isinstance(methods_node, (ast.List, ast.Tuple)):
                for elt in methods_node.elts:
                    val = _get_string_value(elt)
                    if val:
                        m = _METHOD_STR_MAP.get(val.upper())
                        if m:
                            methods_list.append(m)

            if not methods_list:
                methods_list = [HttpMethod.GET]

            return path_str, methods_list

        return None

    @staticmethod
    def _returns_json(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Heuristic: check if the function calls jsonify or returns a dict."""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call) and _get_func_name(node.func) == "jsonify":
                return True
        return False

    @staticmethod
    def _inherits_from_db_model(class_node: ast.ClassDef) -> bool:
        """Check if a class inherits from db.Model."""
        for base in class_node.bases:
            if isinstance(base, ast.Attribute) and base.attr == "Model":
                return True
            if isinstance(base, ast.Name) and base.id == "Model":
                return True
        return False

    def _extract_model(
        self, class_node: ast.ClassDef, source_file: str
    ) -> ModelDefinition | None:
        fields: list[ModelField] = []
        relationships: list[str] = []

        # Extract __tablename__ if present
        table_name = ""
        for stmt in class_node.body:
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name) and t.id == "__tablename__":
                        v = _get_string_value(stmt.value) if isinstance(stmt.value, ast.Constant) else None
                        if v:
                            table_name = v

        for stmt in class_node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            field_name = target.id

            if field_name.startswith("_"):
                continue

            if not isinstance(stmt.value, ast.Call):
                continue

            call = stmt.value
            func_name = _get_func_name(call.func)

            if func_name == "Column":
                field_def = self._parse_column(field_name, call)
                if field_def:
                    fields.append(field_def)
            elif func_name == "relationship":
                # db.relationship("OtherModel", ...)
                if call.args:
                    rel_name = _get_string_value(call.args[0])
                    if rel_name:
                        relationships.append(rel_name)

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
    def _parse_column(field_name: str, call: ast.Call) -> ModelField | None:
        """Parse a db.Column(...) call into a ModelField."""
        field_type = FieldType.UNKNOWN
        max_length: int | None = None
        related_model = ""

        # The first positional arg(s) to Column are the type, e.g. db.String(100), db.Integer
        for arg in call.args:
            if isinstance(arg, ast.Call):
                # e.g. db.String(100), db.ForeignKey("users.id")
                type_name = _get_func_name(arg.func)
                mapped = _SQLALCHEMY_TYPE_MAP.get(type_name)
                if mapped:
                    field_type = mapped
                # Extract length from String(100)
                if type_name == "String" and arg.args:
                    if isinstance(arg.args[0], ast.Constant) and isinstance(arg.args[0].value, int):
                        max_length = arg.args[0].value
                # ForeignKey
                if type_name == "ForeignKey" and arg.args:
                    fk_val = _get_string_value(arg.args[0])
                    if fk_val:
                        related_model = fk_val
                        field_type = FieldType.FOREIGN_KEY
            elif isinstance(arg, ast.Attribute):
                # e.g. db.Integer
                type_name = arg.attr
                mapped = _SQLALCHEMY_TYPE_MAP.get(type_name)
                if mapped:
                    field_type = mapped
            elif isinstance(arg, ast.Name):
                # e.g. Integer (direct import)
                mapped = _SQLALCHEMY_TYPE_MAP.get(arg.id)
                if mapped:
                    field_type = mapped

        unique = _get_bool_keyword(call, "unique") or False
        primary_key = _get_bool_keyword(call, "primary_key") or False
        nullable = _get_bool_keyword(call, "nullable")
        required = not nullable if nullable is not None else True

        default_val = None
        default_node = _get_keyword_value(call, "default")
        if default_node is not None and isinstance(default_node, ast.Constant):
            default_val = str(default_node.value)

        return ModelField(
            name=field_name,
            field_type=field_type,
            required=required,
            unique=unique,
            primary_key=primary_key,
            max_length=max_length,
            default=default_val,
            related_model=related_model,
        )
