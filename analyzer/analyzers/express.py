from __future__ import annotations

import json
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
)

# HTTP methods supported by Express
_HTTP_METHODS = ("get", "post", "put", "delete", "patch", "options", "head")

# app.get('/path', ...) or router.get('/path', ...)
_ROUTE_RE = re.compile(
    r"""(?:app|router)\s*\.\s*("""
    + "|".join(_HTTP_METHODS)
    + r""")\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# app.use('/prefix', someRouter)
_ROUTER_MOUNT_RE = re.compile(
    r"""app\s*\.\s*use\s*\(\s*["']([^"']+)["']\s*,\s*(\w+)""",
)

# Express path param :param
_PATH_PARAM_RE = re.compile(r":(\w+)")

# app.listen(PORT) -- indicator of Express entry point
_APP_LISTEN_RE = re.compile(r"""app\s*\.\s*listen\s*\(""")

# Mongoose schema: new Schema({ ... }) or mongoose.Schema({ ... })
_MONGOOSE_SCHEMA_RE = re.compile(
    r"""(?:new\s+(?:mongoose\.)?Schema|mongoose\.Schema)\s*\(\s*\{(.*?)\}\s*\)""",
    re.DOTALL,
)

# Mongoose model: mongoose.model('Name', schema)
_MONGOOSE_MODEL_RE = re.compile(
    r"""mongoose\s*\.\s*model\s*\(\s*["'](\w+)["']""",
)

# Mongoose field: fieldName: { type: Type, required: true, unique: true }
_MONGOOSE_FIELD_OBJ_RE = re.compile(
    r"""(\w+)\s*:\s*\{([^}]+)\}""",
)

# Mongoose field shorthand: fieldName: Type
_MONGOOSE_FIELD_SHORT_RE = re.compile(
    r"""(\w+)\s*:\s*(String|Number|Boolean|Date|ObjectId|Buffer|Mixed|Map)\b""",
)

# Sequelize model definition: define('ModelName', { ... })
_SEQUELIZE_DEFINE_RE = re.compile(
    r"""\.define\s*\(\s*["'](\w+)["']\s*,\s*\{(.*?)\}\s*[,)]""",
    re.DOTALL,
)

# Sequelize field: fieldName: { type: DataTypes.STRING, ... }
_SEQUELIZE_FIELD_RE = re.compile(
    r"""(\w+)\s*:\s*\{([^}]+)\}""",
)

# Sequelize DataTypes
_SEQUELIZE_TYPE_RE = re.compile(
    r"""(?:DataTypes|Sequelize)\s*\.\s*(\w+)""",
)

# Type mapping for Mongoose types
_MONGOOSE_TYPE_MAP: dict[str, FieldType] = {
    "string": FieldType.STRING,
    "number": FieldType.NUMBER,
    "boolean": FieldType.BOOLEAN,
    "date": FieldType.DATE,
    "objectid": FieldType.FOREIGN_KEY,
    "buffer": FieldType.UNKNOWN,
    "mixed": FieldType.JSON,
    "map": FieldType.JSON,
}

# Type mapping for Sequelize DataTypes
_SEQUELIZE_TYPE_MAP: dict[str, FieldType] = {
    "string": FieldType.STRING,
    "text": FieldType.TEXT,
    "integer": FieldType.INTEGER,
    "bigint": FieldType.INTEGER,
    "float": FieldType.FLOAT,
    "double": FieldType.FLOAT,
    "decimal": FieldType.FLOAT,
    "boolean": FieldType.BOOLEAN,
    "date": FieldType.DATE,
    "dateonly": FieldType.DATE,
    "uuid": FieldType.STRING,
    "json": FieldType.JSON,
    "jsonb": FieldType.JSON,
    "enum": FieldType.SELECT,
}

# Method string to HttpMethod enum
_METHOD_MAP: dict[str, HttpMethod] = {
    "get": HttpMethod.GET,
    "post": HttpMethod.POST,
    "put": HttpMethod.PUT,
    "delete": HttpMethod.DELETE,
    "patch": HttpMethod.PATCH,
    "options": HttpMethod.OPTIONS,
    "head": HttpMethod.HEAD,
}


@register
class ExpressAnalyzer(BaseAnalyzer):
    """Analyzer for Express.js applications."""

    name: str = "express"
    language: str = "javascript"

    def detect(self) -> float:
        """Detect Express by inspecting package.json and source files."""
        confidence = 0.0
        pkg_path = self.source_dir / "package.json"
        if not pkg_path.exists():
            return confidence

        try:
            data = json.loads(self.read_file(pkg_path))
        except (json.JSONDecodeError, OSError):
            return confidence

        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }

        if "express" in all_deps:
            confidence = 0.6

        # Check for route files
        route_files = self.find_files("*route*.*") + self.find_files("*router*.*")
        js_ts_routes = [
            f for f in route_files if f.suffix in (".js", ".ts", ".mjs", ".cjs")
        ]
        if js_ts_routes:
            confidence += 0.2

        # Check for app.listen()
        for fpath in self._get_js_files():
            content = self.read_file(fpath)
            if content and _APP_LISTEN_RE.search(content):
                confidence += 0.2
                break

        return min(confidence, 1.0)

    def analyze_pages(self) -> list:
        """Express is a backend framework -- no frontend pages."""
        return []

    def analyze_endpoints(self) -> list[EndpointDefinition]:
        """Scan JS/TS files for Express route definitions."""
        endpoints: list[EndpointDefinition] = []
        seen: set[tuple[str, str]] = set()

        # First pass: find router mount prefixes
        mount_prefixes = self._find_router_mounts()

        for fpath in self._get_js_files():
            content = self.read_file(fpath)
            if not content:
                continue

            rel = self.relative_path(fpath)

            for m in _ROUTE_RE.finditer(content):
                method_str = m.group(1).lower()
                raw_path = m.group(2)

                # Try to determine if this file has a mounted prefix
                prefix = self._guess_prefix_for_file(fpath, mount_prefixes)
                full_path = prefix + raw_path if prefix else raw_path

                # Normalize path
                full_path = "/" + full_path.strip("/") if full_path != "/" else "/"

                http_method = _METHOD_MAP.get(method_str, HttpMethod.GET)
                key = (http_method.value, full_path)
                if key in seen:
                    continue
                seen.add(key)

                # Extract path params
                path_params = _PATH_PARAM_RE.findall(full_path)

                # Generate a name from method + path
                name_slug = full_path.strip("/").replace("/", "_").replace(":", "")
                name = f"{method_str}_{name_slug}" if name_slug else method_str

                endpoints.append(
                    EndpointDefinition(
                        path=full_path,
                        method=http_method,
                        name=name,
                        source_file=rel,
                        path_params=path_params,
                    )
                )

        return endpoints

    def analyze_models(self) -> list[ModelDefinition]:
        """Scan for Mongoose schemas and Sequelize model definitions."""
        models: list[ModelDefinition] = []
        seen_names: set[str] = set()

        for fpath in self._get_js_files():
            content = self.read_file(fpath)
            if not content:
                continue

            rel = self.relative_path(fpath)

            # Mongoose models
            self._extract_mongoose_models(content, rel, models, seen_names)

            # Sequelize models
            self._extract_sequelize_models(content, rel, models, seen_names)

        return models

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_js_files(self) -> list[Path]:
        """Get all JS/TS source files, excluding node_modules."""
        files = (
            self.find_files("*.js")
            + self.find_files("*.ts")
            + self.find_files("*.mjs")
            + self.find_files("*.cjs")
        )
        return [f for f in files if "node_modules" not in str(f)]

    def _find_router_mounts(self) -> dict[str, str]:
        """Find app.use('/prefix', router) patterns to map variable names to prefixes."""
        mounts: dict[str, str] = {}
        for fpath in self._get_js_files():
            content = self.read_file(fpath)
            if not content:
                continue
            for m in _ROUTER_MOUNT_RE.finditer(content):
                prefix = m.group(1).rstrip("/")
                var_name = m.group(2)
                mounts[var_name] = prefix
        return mounts

    def _guess_prefix_for_file(
        self, fpath: Path, mount_prefixes: dict[str, str]
    ) -> str:
        """Try to guess the route prefix for a file based on router mounts.

        This is a best-effort heuristic: if the filename matches a mounted
        router variable name, use its prefix.
        """
        stem = fpath.stem.lower().replace("router", "").replace("route", "").replace("_", "").replace("-", "")
        for var_name, prefix in mount_prefixes.items():
            var_clean = var_name.lower().replace("router", "").replace("route", "").replace("_", "").replace("-", "")
            if stem and var_clean and stem == var_clean:
                return prefix
        return ""

    def _extract_mongoose_models(
        self,
        content: str,
        source_file: str,
        models: list[ModelDefinition],
        seen: set[str],
    ) -> None:
        """Extract Mongoose model definitions from file content."""
        if "Schema" not in content:
            return

        # Find model name
        model_name_match = _MONGOOSE_MODEL_RE.search(content)
        model_name = model_name_match.group(1) if model_name_match else ""

        for schema_match in _MONGOOSE_SCHEMA_RE.finditer(content):
            schema_body = schema_match.group(1)
            fields = self._parse_mongoose_fields(schema_body)

            if not fields:
                continue

            name = model_name or f"MongooseModel_{len(models)}"
            if name in seen:
                continue
            seen.add(name)

            models.append(
                ModelDefinition(
                    name=name,
                    fields=fields,
                    source_file=source_file,
                    base_class="mongoose.Schema",
                )
            )

    def _parse_mongoose_fields(self, schema_body: str) -> list[ModelField]:
        """Parse fields from a Mongoose Schema body."""
        fields: list[ModelField] = []
        seen_names: set[str] = set()

        # Object-style fields: fieldName: { type: String, required: true }
        for m in _MONGOOSE_FIELD_OBJ_RE.finditer(schema_body):
            field_name = m.group(1)
            field_body = m.group(2)

            if field_name in seen_names or field_name in ("type", "default", "ref"):
                continue
            seen_names.add(field_name)

            # Detect type
            type_match = re.search(
                r"""type\s*:\s*(\w+)""", field_body
            )
            type_str = type_match.group(1).lower() if type_match else "string"
            field_type = _MONGOOSE_TYPE_MAP.get(type_str, FieldType.STRING)

            required = bool(re.search(r"required\s*:\s*true", field_body))
            unique = bool(re.search(r"unique\s*:\s*true", field_body))

            # Detect ref (relationship)
            ref_match = re.search(r"""ref\s*:\s*["'](\w+)["']""", field_body)
            related_model = ref_match.group(1) if ref_match else ""
            if related_model:
                field_type = FieldType.FOREIGN_KEY

            # Detect default value
            default_match = re.search(
                r"""default\s*:\s*["']?([^"',}\s]+)["']?""", field_body
            )
            default_val = default_match.group(1) if default_match else None

            fields.append(
                ModelField(
                    name=field_name,
                    field_type=field_type,
                    required=required,
                    unique=unique,
                    default=default_val,
                    related_model=related_model,
                )
            )

        # Shorthand fields: fieldName: String
        for m in _MONGOOSE_FIELD_SHORT_RE.finditer(schema_body):
            field_name = m.group(1)
            type_str = m.group(2).lower()
            if field_name in seen_names or field_name in ("type", "default", "ref"):
                continue
            seen_names.add(field_name)

            field_type = _MONGOOSE_TYPE_MAP.get(type_str, FieldType.STRING)
            fields.append(
                ModelField(
                    name=field_name,
                    field_type=field_type,
                )
            )

        return fields

    def _extract_sequelize_models(
        self,
        content: str,
        source_file: str,
        models: list[ModelDefinition],
        seen: set[str],
    ) -> None:
        """Extract Sequelize model definitions from file content."""
        if "define" not in content:
            return

        for define_match in _SEQUELIZE_DEFINE_RE.finditer(content):
            model_name = define_match.group(1)
            fields_body = define_match.group(2)

            if model_name in seen:
                continue

            fields = self._parse_sequelize_fields(fields_body)
            if not fields:
                continue

            seen.add(model_name)

            # Derive table name (Sequelize pluralizes by default)
            table_name = model_name.lower() + "s"

            models.append(
                ModelDefinition(
                    name=model_name,
                    fields=fields,
                    source_file=source_file,
                    table_name=table_name,
                    base_class="sequelize.Model",
                )
            )

    def _parse_sequelize_fields(self, fields_body: str) -> list[ModelField]:
        """Parse fields from a Sequelize model definition body."""
        fields: list[ModelField] = []
        seen_names: set[str] = set()

        for m in _SEQUELIZE_FIELD_RE.finditer(fields_body):
            field_name = m.group(1)
            field_body = m.group(2)

            if field_name in seen_names:
                continue
            seen_names.add(field_name)

            # Detect DataType
            type_match = _SEQUELIZE_TYPE_RE.search(field_body)
            type_str = type_match.group(1).lower() if type_match else "string"
            field_type = _SEQUELIZE_TYPE_MAP.get(type_str, FieldType.STRING)

            required = bool(re.search(r"allowNull\s*:\s*false", field_body))
            unique = bool(re.search(r"unique\s*:\s*true", field_body))
            primary_key = bool(re.search(r"primaryKey\s*:\s*true", field_body))

            # Default value
            default_match = re.search(
                r"""defaultValue\s*:\s*["']?([^"',}\s]+)["']?""", field_body
            )
            default_val = default_match.group(1) if default_match else None

            fields.append(
                ModelField(
                    name=field_name,
                    field_type=field_type,
                    required=required,
                    unique=unique,
                    primary_key=primary_key,
                    default=default_val,
                )
            )

        return fields
