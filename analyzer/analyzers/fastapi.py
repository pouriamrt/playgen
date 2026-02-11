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

_PYDANTIC_FIELD_MAP: dict[str, FieldType] = {
    "str": FieldType.STRING,
    "int": FieldType.INTEGER,
    "float": FieldType.FLOAT,
    "bool": FieldType.BOOLEAN,
    "date": FieldType.DATE,
    "datetime": FieldType.DATETIME,
    "bytes": FieldType.FILE,
    "list": FieldType.JSON,
    "dict": FieldType.JSON,
    "List": FieldType.JSON,
    "Dict": FieldType.JSON,
    "Optional": FieldType.UNKNOWN,
    "EmailStr": FieldType.EMAIL,
    "HttpUrl": FieldType.URL,
    "UUID": FieldType.STRING,
}

_ROUTE_METHOD_MAP: dict[str, HttpMethod] = {
    "get": HttpMethod.GET,
    "post": HttpMethod.POST,
    "put": HttpMethod.PUT,
    "patch": HttpMethod.PATCH,
    "delete": HttpMethod.DELETE,
    "options": HttpMethod.OPTIONS,
    "head": HttpMethod.HEAD,
}


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


def _get_annotation_name(node: ast.expr) -> str:
    """Extract the type name from an annotation AST node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    # Handle generic types like Optional[str], list[int]
    if isinstance(node, ast.Subscript):
        return _get_annotation_name(node.value)
    return ""


@register
class FastAPIAnalyzer(BaseAnalyzer):
    """Analyzer for FastAPI projects."""

    name: str = "fastapi"
    language: str = "python"

    def detect(self) -> float:
        confidence = 0.0

        # Check for fastapi imports in .py files
        import_found = False
        for py_file in self.find_files("*.py"):
            tree = self._parse_file(py_file)
            if tree is None:
                continue
            if self._has_fastapi_import(tree):
                import_found = True
                break

        if import_found:
            confidence += 0.5

        # Check dependency files
        if self._check_dependency_files("fastapi"):
            confidence += 0.3

        # Check for FastAPI() instantiation in main.py
        for main_file in self.find_files("main.py"):
            tree = self._parse_file(main_file)
            if tree is None:
                continue
            if self._has_fastapi_app(tree):
                confidence += 0.2
                break

        return min(confidence, 1.0)

    def analyze_endpoints(self) -> list[EndpointDefinition]:
        endpoints: list[EndpointDefinition] = []

        # Build a mapping of source file -> route prefix
        file_prefixes = self._find_router_prefixes()

        for py_file in self.find_files("*.py"):
            tree = self._parse_file(py_file)
            if tree is None:
                continue
            rel = self.relative_path(py_file)
            prefix = file_prefixes.get(rel, "")
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
                if not self._inherits_from_basemodel(node):
                    continue
                model_def = self._extract_model(node, rel)
                if model_def:
                    models.append(model_def)

        return models

    def analyze_pages(self) -> list[PageDefinition]:
        # FastAPI is a backend framework; no pages to discover.
        return []

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
    def _has_fastapi_import(tree: ast.Module) -> bool:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "fastapi" or alias.name.startswith("fastapi."):
                        return True
            if isinstance(node, ast.ImportFrom):
                if node.module and (
                    node.module == "fastapi" or node.module.startswith("fastapi.")
                ):
                    return True
        return False

    @staticmethod
    def _has_fastapi_app(tree: ast.Module) -> bool:
        """Check if the file contains `FastAPI()` instantiation."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _get_func_name(node.func) == "FastAPI":
                return True
        return False

    def _check_dependency_files(self, package_name: str) -> bool:
        """Check if a package appears in requirements.txt or pyproject.toml."""
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

        # Combine include_router prefix with local APIRouter prefix
        include_prefix = prefix
        local_prefix = self._find_local_router_prefix(tree)
        if include_prefix and local_prefix:
            prefix = include_prefix.rstrip("/") + "/" + local_prefix.lstrip("/")
        elif local_prefix:
            prefix = local_prefix

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                endpoint = self._parse_route_decorator(
                    decorator, node, source_file, prefix
                )
                if endpoint:
                    endpoints.append(endpoint)

        return endpoints

    def _parse_route_decorator(
        self,
        decorator: ast.expr,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_file: str,
        prefix: str = "",
    ) -> EndpointDefinition | None:
        """Parse a decorator like @app.get("/path") or @router.post("/path")."""
        if not isinstance(decorator, ast.Call):
            return None

        # The decorator func must be an attribute like app.get, router.post
        if not isinstance(decorator.func, ast.Attribute):
            return None

        method_name = decorator.func.attr
        http_method = _ROUTE_METHOD_MAP.get(method_name)
        if http_method is None:
            return None

        # First positional arg is the path
        if not decorator.args:
            return None
        path_str = _get_string_value(decorator.args[0])
        if path_str is None:
            return None

        # Prepend the router mount prefix
        if prefix:
            path_str = prefix.rstrip("/") + "/" + path_str.lstrip("/")
            path_str = "/" + path_str.lstrip("/")

        # Extract path parameters from {param} syntax
        path_params = re.findall(r"\{(\w+)\}", path_str)

        # Check for response_model keyword
        response_model = ""
        rm_node = self._get_keyword_value(decorator, "response_model")
        if rm_node is not None:
            response_model = _get_annotation_name(rm_node)

        # Extract request_model from function parameter annotations
        # Skip 'self', path params, and built-in types — the remaining
        # typed parameter whose annotation is a class name is the body model
        request_model = ""
        builtin_types = {"str", "int", "float", "bool", "bytes", "Request", "Response"}
        for arg in func_node.args.args:
            if arg.arg in ("self", "cls", "request", "response"):
                continue
            if arg.arg in path_params:
                continue
            if arg.annotation:
                ann_name = _get_annotation_name(arg.annotation)
                if ann_name and ann_name not in builtin_types:
                    request_model = ann_name
                    break

        return EndpointDefinition(
            path=path_str,
            method=http_method,
            name=func_node.name,
            view_name=func_node.name,
            source_file=source_file,
            path_params=path_params,
            response_model=response_model,
            request_model=request_model,
        )

    @staticmethod
    def _get_keyword_value(call: ast.Call, keyword_name: str) -> ast.expr | None:
        for kw in call.keywords:
            if kw.arg == keyword_name:
                return kw.value
        return None

    @staticmethod
    def _find_local_router_prefix(tree: ast.Module) -> str:
        """Find APIRouter(prefix="/...") defined in the same file."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _get_func_name(node.func) != "APIRouter":
                continue
            for kw in node.keywords:
                if kw.arg == "prefix":
                    val = _get_string_value(kw.value)
                    if val:
                        return val
        return ""

    def _find_router_prefixes(self) -> dict[str, str]:
        """Build a mapping of source_file -> prefix from include_router() calls.

        Handles patterns like:
            from app.routers import test
            app.include_router(test.router, prefix="/test")
        and:
            from app.routers.test import router as test_router
            app.include_router(test_router, prefix="/test")
        """
        prefixes: dict[str, str] = {}

        for py_file in self.find_files("*.py"):
            tree = self._parse_file(py_file)
            if tree is None:
                continue

            # Collect imports in this file: var_name -> module_path
            imports: dict[str, str] = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports[name] = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports[name] = alias.name

            # Find include_router() calls
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr != "include_router":
                    continue
                if not node.args:
                    continue

                # Extract prefix keyword
                prefix_val = ""
                for kw in node.keywords:
                    if kw.arg == "prefix":
                        prefix_val = _get_string_value(kw.value) or ""
                if not prefix_val:
                    continue

                # Resolve the router arg to a source file
                router_arg = node.args[0]
                module_path = ""

                if isinstance(router_arg, ast.Attribute):
                    # Pattern: module.router
                    if isinstance(router_arg.value, ast.Name):
                        module_path = imports.get(router_arg.value.id, "")
                elif isinstance(router_arg, ast.Name):
                    # Pattern: router_var (imported directly)
                    module_path = imports.get(router_arg.id, "")

                if not module_path:
                    continue

                resolved = self._resolve_module_to_file(module_path)
                if resolved:
                    prefixes[resolved] = prefix_val

        return prefixes

    def _resolve_module_to_file(self, module_path: str) -> str | None:
        """Resolve a dotted Python module path to a relative file path."""
        parts = module_path.split(".")
        for py_file in self.find_files("*.py"):
            rel = self.relative_path(py_file)
            rel_parts = Path(rel).with_suffix("").parts
            if len(rel_parts) >= len(parts) and rel_parts[-len(parts):] == tuple(parts):
                return rel
        return None

    @staticmethod
    def _inherits_from_basemodel(class_node: ast.ClassDef) -> bool:
        for base in class_node.bases:
            name = _get_annotation_name(base)
            if name in ("BaseModel", "BaseSchema"):
                return True
        return False

    def _extract_model(
        self, class_node: ast.ClassDef, source_file: str
    ) -> ModelDefinition | None:
        fields: list[ModelField] = []

        for stmt in class_node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id
                # Skip private/dunder attrs and Config inner class references
                if field_name.startswith("_"):
                    continue

                annotation = stmt.annotation
                type_name = _get_annotation_name(annotation)
                field_type = _PYDANTIC_FIELD_MAP.get(type_name, FieldType.UNKNOWN)

                # Determine if optional
                required = True
                if isinstance(annotation, ast.Subscript):
                    wrapper_name = _get_annotation_name(annotation.value)
                    if wrapper_name == "Optional":
                        required = False
                        # Unwrap the inner type
                        if isinstance(annotation.slice, ast.Name):
                            inner = annotation.slice.id
                            field_type = _PYDANTIC_FIELD_MAP.get(inner, field_type)

                # Check for default value
                default_val = None
                if stmt.value is not None:
                    if isinstance(stmt.value, ast.Constant):
                        default_val = str(stmt.value.value)
                        required = False
                    elif isinstance(stmt.value, ast.Call):
                        # Field(...) or similar
                        fname = _get_func_name(stmt.value.func)
                        if fname == "Field":
                            default_node = self._get_keyword_value(stmt.value, "default")
                            if default_node and isinstance(default_node, ast.Constant):
                                default_val = str(default_node.value)
                                required = False
                        else:
                            # Could be a factory default
                            required = False

                fields.append(
                    ModelField(
                        name=field_name,
                        field_type=field_type,
                        required=required,
                        default=default_val,
                    )
                )

        base_class = ""
        if class_node.bases:
            base_class = _get_annotation_name(class_node.bases[0])

        return ModelDefinition(
            name=class_node.name,
            fields=fields,
            source_file=source_file,
            base_class=base_class,
        )
