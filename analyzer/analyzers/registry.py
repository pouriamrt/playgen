from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analyzer.analyzers.base import BaseAnalyzer

_registry: list[type[BaseAnalyzer]] = []


def register(cls: type[BaseAnalyzer]) -> type[BaseAnalyzer]:
    """Decorator to register an analyzer class in the global registry."""
    _registry.append(cls)
    return cls


def get_all_analyzers() -> list[type[BaseAnalyzer]]:
    """Return all registered analyzer classes."""
    return list(_registry)


def load_all_analyzers() -> None:
    """Import all analyzer modules so their @register decorators fire."""
    import analyzer.analyzers.angular  # noqa: F401
    import analyzer.analyzers.django  # noqa: F401
    import analyzer.analyzers.express  # noqa: F401
    import analyzer.analyzers.fastapi  # noqa: F401
    import analyzer.analyzers.flask  # noqa: F401
    import analyzer.analyzers.react  # noqa: F401
    import analyzer.analyzers.vue  # noqa: F401
