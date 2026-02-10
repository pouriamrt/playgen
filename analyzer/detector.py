from __future__ import annotations

from pathlib import Path

from analyzer.analyzers.base import BaseAnalyzer
from analyzer.analyzers.registry import get_all_analyzers, load_all_analyzers
from analyzer.schema import TechStackInfo


def detect_tech_stack(
    source_dir: str | Path, threshold: float = 0.3
) -> list[tuple[BaseAnalyzer, TechStackInfo]]:
    """Run all registered analyzers' detect() and return matches above threshold.

    Returns a list of (analyzer_instance, TechStackInfo) sorted by confidence descending.
    """
    load_all_analyzers()

    results: list[tuple[BaseAnalyzer, TechStackInfo]] = []

    for analyzer_cls in get_all_analyzers():
        analyzer = analyzer_cls(source_dir)
        confidence = analyzer.detect()

        if confidence >= threshold:
            info = TechStackInfo(
                framework=analyzer.name,
                confidence=confidence,
                language=analyzer.language,
            )
            results.append((analyzer, info))

    results.sort(key=lambda x: x[1].confidence, reverse=True)
    return results
