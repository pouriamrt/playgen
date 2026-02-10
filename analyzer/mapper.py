from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from analyzer.schema import (
    DiscoveryResult,
    EndpointDefinition,
    FormDefinition,
    FrontendBackendMapping,
    HttpMethod,
    PageDefinition,
)


def _normalize_path(path: str) -> str:
    """Strip trailing slashes and lowercase a URL path for comparison."""
    return path.rstrip("/").lower()


def _strip_param_segments(path: str) -> str:
    """Replace path parameter placeholders with a wildcard token.

    Handles ``{id}``, ``:id``, and ``<id>`` styles so that
    ``/api/users/{id}`` and ``/api/users/:id`` both become
    ``/api/users/*``.
    """
    path = re.sub(r"\{[^}]+\}", "*", path)
    path = re.sub(r":[a-zA-Z_]\w*", "*", path)
    path = re.sub(r"<[^>]+>", "*", path)
    return path


# ── Strategy 1: URL path matching ────────────────────────────────────────


def _match_by_url(
    pages: list[PageDefinition],
    endpoints: list[EndpointDefinition],
) -> list[FrontendBackendMapping]:
    """Match form ``action_url`` directly against endpoint ``path``."""
    mappings: list[FrontendBackendMapping] = []

    for page in pages:
        for form in page.forms:
            if not form.action_url:
                continue
            form_path = _normalize_path(form.action_url)
            form_path_wild = _strip_param_segments(form_path)

            for ep in endpoints:
                ep_path = _normalize_path(ep.path)
                ep_path_wild = _strip_param_segments(ep_path)

                if form_path == ep_path:
                    confidence = 0.9
                elif form_path_wild == ep_path_wild:
                    confidence = 0.8
                else:
                    continue

                # Prefer matching HTTP methods when form declares one
                if form.method != ep.method:
                    confidence -= 0.05

                mappings.append(
                    FrontendBackendMapping(
                        page_name=page.name,
                        form_name=form.name,
                        endpoint_path=ep.path,
                        endpoint_method=ep.method,
                        confidence=round(confidence, 2),
                        strategy="url_path",
                    )
                )

    return mappings


# ── Strategy 2: Name / convention matching ───────────────────────────────


_CRUD_VERBS = {
    "create": HttpMethod.POST,
    "add": HttpMethod.POST,
    "new": HttpMethod.POST,
    "edit": HttpMethod.PUT,
    "update": HttpMethod.PUT,
    "delete": HttpMethod.DELETE,
    "remove": HttpMethod.DELETE,
    "list": HttpMethod.GET,
    "detail": HttpMethod.GET,
    "view": HttpMethod.GET,
    "show": HttpMethod.GET,
}


def _tokenize_name(name: str) -> list[str]:
    """Split a name such as ``user-create`` or ``UserCreate`` into tokens."""
    # Replace common separators with spaces
    name = re.sub(r"[-_/]", " ", name)
    # Insert space before uppercase letters (camelCase/PascalCase)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return [t.lower() for t in name.split() if t]


def _match_by_convention(
    pages: list[PageDefinition],
    endpoints: list[EndpointDefinition],
) -> list[FrontendBackendMapping]:
    """Match page/form names to endpoint names using CRUD conventions."""
    mappings: list[FrontendBackendMapping] = []

    for page in pages:
        page_tokens = set(_tokenize_name(page.name))

        for ep in endpoints:
            ep_tokens = set(_tokenize_name(ep.name or ep.path))
            shared = page_tokens & ep_tokens

            if not shared:
                continue

            # Base confidence from token overlap
            confidence = min(0.5 + 0.1 * len(shared), 0.7)

            # Boost if a CRUD verb aligns with the HTTP method
            for token in shared:
                expected_method = _CRUD_VERBS.get(token)
                if expected_method and expected_method == ep.method:
                    confidence = min(confidence + 0.05, 0.7)

            mappings.append(
                FrontendBackendMapping(
                    page_name=page.name,
                    form_name="",
                    endpoint_path=ep.path,
                    endpoint_method=ep.method,
                    confidence=round(confidence, 2),
                    strategy="name_convention",
                )
            )

    return mappings


# ── Strategy 3: fetch/axios reference tracing ────────────────────────────

_FETCH_PATTERNS = [
    # fetch('/api/...') or fetch("/api/...")
    re.compile(r"""fetch\(\s*['"]([^'"]+)['"]\s*"""),
    # axios.get/post/put/delete('/api/...')
    re.compile(r"""axios\.\w+\(\s*['"]([^'"]+)['"]\s*"""),
    # $.ajax({ url: '/api/...' })
    re.compile(r"""url\s*:\s*['"]([^'"]+)['"]\s*"""),
]

_AXIOS_METHOD_PATTERN = re.compile(
    r"""axios\.(get|post|put|patch|delete)\(\s*['"]([^'"]+)['"]"""
)
_FETCH_OPTIONS_PATTERN = re.compile(
    r"""fetch\(\s*['"][^'"]+['"]\s*,\s*\{[^}]*method\s*:\s*['"](\w+)['"]""",
    re.DOTALL,
)


def _match_by_fetch_references(
    pages: list[PageDefinition],
    endpoints: list[EndpointDefinition],
    source_dir: str = "",
) -> list[FrontendBackendMapping]:
    """Scan source files associated with pages for fetch/axios calls."""
    mappings: list[FrontendBackendMapping] = []

    ep_paths = {_normalize_path(ep.path): ep for ep in endpoints}
    ep_paths_wild = {_strip_param_segments(_normalize_path(ep.path)): ep for ep in endpoints}

    base_dir = Path(source_dir) if source_dir else None

    for page in pages:
        if not page.source_file:
            continue

        source_path = Path(page.source_file)
        # Resolve relative paths against the project source directory
        if not source_path.is_absolute() and base_dir:
            source_path = base_dir / source_path
        if not source_path.is_file():
            continue

        try:
            source_text = source_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        found_urls: set[str] = set()
        for pattern in _FETCH_PATTERNS:
            for match in pattern.finditer(source_text):
                found_urls.add(match.group(1))

        for url in found_urls:
            url_path = _normalize_path(urlparse(url).path)
            url_path_wild = _strip_param_segments(url_path)

            ep = ep_paths.get(url_path) or ep_paths_wild.get(url_path_wild)
            if not ep:
                continue

            # Try to determine the HTTP method from the source call
            inferred_method = ep.method
            for m in _AXIOS_METHOD_PATTERN.finditer(source_text):
                if _normalize_path(m.group(2)) == url_path:
                    inferred_method = HttpMethod(m.group(1).upper())
                    break
            for m in _FETCH_OPTIONS_PATTERN.finditer(source_text):
                inferred_method = HttpMethod(m.group(1).upper())
                break

            confidence = 0.6 if url_path in ep_paths else 0.4

            mappings.append(
                FrontendBackendMapping(
                    page_name=page.name,
                    form_name="",
                    endpoint_path=ep.path,
                    endpoint_method=inferred_method,
                    confidence=round(confidence, 2),
                    strategy="fetch_reference",
                )
            )

    return mappings


# ── Public API ────────────────────────────────────────────────────────────


def _deduplicate(mappings: list[FrontendBackendMapping]) -> list[FrontendBackendMapping]:
    """Keep only the highest-confidence mapping per (page, endpoint) pair."""
    best: dict[tuple[str, str, str], FrontendBackendMapping] = {}
    for m in mappings:
        key = (m.page_name, m.endpoint_path, m.endpoint_method.value)
        existing = best.get(key)
        if existing is None or m.confidence > existing.confidence:
            best[key] = m
    return sorted(best.values(), key=lambda m: -m.confidence)


def map_frontend_to_backend(
    discovery: DiscoveryResult,
) -> list[FrontendBackendMapping]:
    """Run all mapping strategies and return deduplicated results."""
    all_mappings: list[FrontendBackendMapping] = []

    all_mappings.extend(_match_by_url(discovery.pages, discovery.endpoints))
    all_mappings.extend(_match_by_convention(discovery.pages, discovery.endpoints))
    all_mappings.extend(
        _match_by_fetch_references(
            discovery.pages, discovery.endpoints, discovery.source_dir
        )
    )

    return _deduplicate(all_mappings)
