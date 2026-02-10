from __future__ import annotations

import json
import re
from pathlib import Path

from analyzer.analyzers.base import BaseAnalyzer
from analyzer.analyzers.react import ReactAnalyzer, _component_to_name
from analyzer.analyzers.registry import register
from analyzer.schema import (
    EndpointDefinition,
    HttpMethod,
    PageDefinition,
)

# Regex for exported HTTP handler functions in App Router route files
_APP_ROUTER_HANDLER_RE = re.compile(
    r"""export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b"""
)

# Regex for req.method === 'METHOD' in Pages Router API files
_PAGES_API_METHOD_RE = re.compile(
    r"""req\.method\s*===?\s*["'](GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)["']"""
)

# Route group pattern: directory names wrapped in parentheses like (auth), (dashboard)
_ROUTE_GROUP_RE = re.compile(r"\([^)]+\)")


@register
class NextjsAnalyzer(ReactAnalyzer):
    """Analyzer for Next.js 14+ applications (App Router & Pages Router)."""

    name: str = "nextjs"
    language: str = "typescript"

    def detect(self) -> float:
        """Detect Next.js by scanning all immediate subdirectories for package.json with 'next'."""
        confidence = 0.0

        # Build candidates: root + ALL immediate subdirectories
        candidates: list[Path] = [self.source_dir / "package.json"]
        try:
            for entry in self.source_dir.iterdir():
                if entry.is_dir() and entry.name not in self._EXCLUDE_DIRS:
                    pkg = entry / "package.json"
                    if pkg.exists():
                        candidates.append(pkg)
        except OSError:
            pass

        data = None
        found_pkg_path: Path | None = None
        for pkg_path in candidates:
            if not pkg_path.exists():
                continue
            try:
                data = json.loads(self.read_file(pkg_path))
            except (json.JSONDecodeError, OSError):
                continue

            all_deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }
            if "next" in all_deps:
                found_pkg_path = pkg_path
                break
            # Reset data if this package.json doesn't have next
            data = None

        if data is None or found_pkg_path is None:
            return 0.0

        # Base confidence for finding 'next' in dependencies
        confidence = 0.8

        # Remember the frontend directory if it's a subdirectory
        frontend_dir = found_pkg_path.parent
        if frontend_dir != self.source_dir:
            self._frontend_dir = frontend_dir
        else:
            self._frontend_dir = None

        search_root = self._frontend_dir or self.source_dir

        # Bonus for app/ directory (App Router)
        for app_dir_name in ("app", "src/app"):
            if (search_root / app_dir_name).is_dir():
                confidence += 0.1
                break

        # Bonus for next.config.* file
        for config_name in ("next.config.js", "next.config.mjs", "next.config.ts"):
            if (search_root / config_name).exists():
                confidence += 0.1
                break

        return min(confidence, 1.0)

    def analyze_pages(self) -> list[PageDefinition]:
        """Discover pages from Next.js file-based routing with route group support."""
        pages: list[PageDefinition] = []
        seen_paths: set[str] = set()

        # Scan Next.js file-based routing (pages/ and app/ directories)
        self._scan_nextjs_pages(pages, seen_paths)

        # Also scan for React Router routes (some Next.js apps use both)
        self._scan_router_routes(pages, seen_paths)

        return pages

    def _collect_nextjs_app_routes(
        self,
        base_dir: Path,
        current_dir: Path,
        pages: list[PageDefinition],
        seen: set[str],
    ) -> None:
        """Recursively collect routes from Next.js app/ directory.

        Strips route groups like (auth) from URL paths and handles
        catch-all [...slug] and optional catch-all [[...slug]] segments.
        """
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
                    if part == ".":
                        continue
                    # Strip route groups: (auth), (dashboard), etc.
                    if _ROUTE_GROUP_RE.fullmatch(part):
                        continue
                    # Optional catch-all: [[...slug]]
                    if part.startswith("[[...") and part.endswith("]]"):
                        param = part[5:-2]
                        route_parts.append(f":*{param}?")
                    # Catch-all: [...slug]
                    elif part.startswith("[...") and part.endswith("]"):
                        param = part[4:-1]
                        route_parts.append(f":*{param}")
                    # Dynamic segment: [id]
                    elif part.startswith("[") and part.endswith("]"):
                        route_parts.append(f":{part[1:-1]}")
                    else:
                        route_parts.append(part)

                route_path = "/" + "/".join(route_parts) if route_parts else "/"

                if route_path not in seen:
                    seen.add(route_path)
                    dir_name = entry.parent.name if entry.parent != base_dir else "Home"
                    # If dir_name is a route group, walk up to find a real name
                    if _ROUTE_GROUP_RE.fullmatch(dir_name):
                        dir_name = "Home"
                    pages.append(
                        PageDefinition(
                            name=_component_to_name(dir_name),
                            path=route_path,
                            component=dir_name,
                            source_file=self.relative_path(entry),
                        )
                    )

    def analyze_endpoints(self) -> list[EndpointDefinition]:
        """Detect API routes from App Router and Pages Router."""
        endpoints: list[EndpointDefinition] = []
        seen: set[tuple[str, str]] = set()

        roots = [self.source_dir]
        if self._frontend_dir:
            roots.insert(0, self._frontend_dir)

        for root in roots:
            self._scan_app_router_api(root, endpoints, seen)
            self._scan_pages_router_api(root, endpoints, seen)

        return endpoints

    def _scan_app_router_api(
        self,
        root: Path,
        endpoints: list[EndpointDefinition],
        seen: set[tuple[str, str]],
    ) -> None:
        """Scan App Router api routes: app/api/**/route.ts|js."""
        for app_dir_name in ("app", "src/app"):
            api_dir = root / app_dir_name / "api"
            if not api_dir.is_dir():
                continue

            base_dir = root / app_dir_name

            for route_file in api_dir.rglob("route.*"):
                if route_file.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                    continue
                if any(part in self._EXCLUDE_DIRS for part in route_file.parts):
                    continue

                content = self.read_file(route_file)
                if not content:
                    continue

                # Build the API path from the file location
                rel_to_app = route_file.parent.relative_to(base_dir)
                parts = list(rel_to_app.parts)

                path_parts = []
                for part in parts:
                    if part == ".":
                        continue
                    if _ROUTE_GROUP_RE.fullmatch(part):
                        continue
                    if part.startswith("[[...") and part.endswith("]]"):
                        param = part[5:-2]
                        path_parts.append(f":*{param}?")
                    elif part.startswith("[...") and part.endswith("]"):
                        param = part[4:-1]
                        path_parts.append(f":*{param}")
                    elif part.startswith("[") and part.endswith("]"):
                        path_parts.append(f":{part[1:-1]}")
                    else:
                        path_parts.append(part)

                api_path = "/" + "/".join(path_parts)
                rel_file = self.relative_path(route_file)

                # Find exported handler functions
                methods_found = _APP_ROUTER_HANDLER_RE.findall(content)
                if not methods_found:
                    # If no explicit handlers found, assume GET as default
                    methods_found = ["GET"]

                for method_str in methods_found:
                    key = (method_str.upper(), api_path)
                    if key in seen:
                        continue
                    seen.add(key)
                    method = HttpMethod(method_str.upper())
                    endpoints.append(
                        EndpointDefinition(
                            path=api_path,
                            method=method,
                            name=f"{method_str.upper()} {api_path}",
                            source_file=rel_file,
                        )
                    )

    def _scan_pages_router_api(
        self,
        root: Path,
        endpoints: list[EndpointDefinition],
        seen: set[tuple[str, str]],
    ) -> None:
        """Scan Pages Router api routes: pages/api/**/*.ts|js."""
        for pages_dir_name in ("pages", "src/pages"):
            api_dir = root / pages_dir_name / "api"
            if not api_dir.is_dir():
                continue

            for api_file in api_dir.rglob("*"):
                if api_file.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                    continue
                if api_file.is_dir():
                    continue
                if any(part in self._EXCLUDE_DIRS for part in api_file.parts):
                    continue

                content = self.read_file(api_file)
                if not content:
                    continue

                # Build path from file location
                rel_to_api = api_file.relative_to(api_dir)
                parts = list(rel_to_api.parts)
                # Remove extension from last part
                parts[-1] = api_file.stem

                path_parts = []
                for part in parts:
                    if part.startswith("[") and part.endswith("]"):
                        path_parts.append(f":{part[1:-1]}")
                    elif part == "index":
                        continue
                    else:
                        path_parts.append(part)

                api_path = "/api/" + "/".join(path_parts) if path_parts else "/api"
                rel_file = self.relative_path(api_file)

                # Detect methods from req.method checks
                methods_found = list(set(_PAGES_API_METHOD_RE.findall(content)))
                if not methods_found:
                    # Default handler responds to all methods; report common ones
                    methods_found = ["GET", "POST"]

                for method_str in methods_found:
                    key = (method_str.upper(), api_path)
                    if key in seen:
                        continue
                    seen.add(key)
                    method = HttpMethod(method_str.upper())
                    endpoints.append(
                        EndpointDefinition(
                            path=api_path,
                            method=method,
                            name=f"{method_str.upper()} {api_path}",
                            source_file=rel_file,
                        )
                    )

    def analyze_models(self) -> list:
        """Next.js is a frontend framework -- no data models."""
        return []
