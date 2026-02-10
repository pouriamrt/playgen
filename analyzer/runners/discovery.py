from __future__ import annotations

from pathlib import Path

from analyzer.detector import detect_tech_stack
from analyzer.mapper import map_frontend_to_backend
from analyzer.schema import DiscoveryResult, FormDefinition, PageDefinition


def _attach_forms_to_pages(
    pages: list[PageDefinition], forms: list[FormDefinition]
) -> None:
    """Attach discovered forms to pages that share the same source_file.

    Forms discovered by analyze_forms() are returned as a flat list.  The
    templates iterate ``page.forms``, so we need to copy each form into the
    matching page.  Forms that don't match any page are left in the top-level
    list for reference but won't generate page-specific tests.
    """
    # Build a lookup from source_file → page
    page_by_source: dict[str, list[PageDefinition]] = {}
    for page in pages:
        if page.source_file:
            page_by_source.setdefault(page.source_file, []).append(page)

    attached_names: set[tuple[str, str]] = set()
    for page in pages:
        for form in page.forms:
            attached_names.add((page.source_file, form.name))

    for form in forms:
        if not form.source_file:
            continue
        matching_pages = page_by_source.get(form.source_file, [])
        for page in matching_pages:
            if (page.source_file, form.name) not in attached_names:
                page.forms.append(form)
                attached_names.add((page.source_file, form.name))

    # If no pages matched any form, attach all forms to the first page
    # (common for SPAs where forms are in child components, not App.jsx)
    if pages and not any(page.forms for page in pages):
        for form in forms:
            pages[0].forms.append(form)


def run_discovery(
    source_dir: str | Path,
    output_path: str | Path | None = None,
) -> DiscoveryResult:
    """Run all detected analyzers on source_dir and produce a DiscoveryResult."""
    source_dir = Path(source_dir)

    if not source_dir.is_dir():
        print(f"Error: {source_dir} is not a valid directory")
        return DiscoveryResult(source_dir=str(source_dir))

    print(f"Discovering components in {source_dir} ...")

    # 1. Detect tech stack
    detected = detect_tech_stack(source_dir)
    if not detected:
        print(f"No supported frameworks detected in {source_dir}")
        return DiscoveryResult(source_dir=str(source_dir))

    # 2. Run each detected analyzer
    all_pages, all_endpoints, all_models, all_forms = [], [], [], []
    tech_stack = []
    for analyzer, info in detected:
        print(f"  Analyzing {info.framework} (confidence: {info.confidence:.1%})...")
        tech_stack.append(info)
        all_pages.extend(analyzer.analyze_pages())
        all_endpoints.extend(analyzer.analyze_endpoints())
        all_models.extend(analyzer.analyze_models())
        all_forms.extend(analyzer.analyze_forms())

    # 2b. Attach standalone forms to their pages by matching source_file
    _attach_forms_to_pages(all_pages, all_forms)

    # 3. Build discovery result
    discovery = DiscoveryResult(
        source_dir=str(source_dir),
        tech_stack=tech_stack,
        pages=all_pages,
        endpoints=all_endpoints,
        models=all_models,
        forms=all_forms,
    )

    # 4. Map frontend to backend
    discovery.mappings = map_frontend_to_backend(discovery)

    # 5. Print summary
    print(f"  Found {len(all_pages)} pages, {len(all_endpoints)} endpoints, "
          f"{len(all_models)} models, {len(all_forms)} forms, "
          f"{len(discovery.mappings)} mappings")

    # 6. Save to file if requested
    if output_path:
        discovery.to_json_file(output_path)
        print(f"  Discovery saved to {output_path}")

    return discovery
