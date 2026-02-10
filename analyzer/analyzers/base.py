from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from analyzer.schema import (
    EndpointDefinition,
    FormDefinition,
    ModelDefinition,
    PageDefinition,
)


class BaseAnalyzer(ABC):
    """Abstract base class for all framework-specific analyzers."""

    name: str = "base"
    language: str = "unknown"

    def __init__(self, source_dir: str | Path) -> None:
        self.source_dir = Path(source_dir)

    @abstractmethod
    def detect(self) -> float:
        """Detect if this framework is used in the source directory.

        Returns a confidence score between 0.0 and 1.0.
        """

    @abstractmethod
    def analyze_pages(self) -> list[PageDefinition]:
        """Discover pages/routes in the source code."""

    @abstractmethod
    def analyze_endpoints(self) -> list[EndpointDefinition]:
        """Discover API endpoints in the source code."""

    @abstractmethod
    def analyze_models(self) -> list[ModelDefinition]:
        """Discover data models in the source code."""

    def analyze_forms(self) -> list[FormDefinition]:
        """Discover forms in the source code. Override in subclasses."""
        return []

    def find_files(self, pattern: str) -> list[Path]:
        """Find files matching a glob pattern relative to source_dir."""
        return sorted(self.source_dir.rglob(pattern))

    def read_file(self, path: Path) -> str:
        """Read a file and return its contents, or empty string on error."""
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def relative_path(self, path: Path) -> str:
        """Return the path relative to source_dir as a string."""
        try:
            return str(path.relative_to(self.source_dir))
        except ValueError:
            return str(path)
