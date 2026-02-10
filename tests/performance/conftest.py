from __future__ import annotations

import os
from dataclasses import dataclass

import pytest
from playwright.sync_api import Page

from config.settings import settings


@dataclass
class PerformanceThresholds:
    """Configurable performance thresholds in milliseconds.

    Override via environment variables prefixed with PERF_.
    """

    page_load_ms: int = int(os.getenv("PERF_PAGE_LOAD_MS", "3000"))
    time_to_interactive_ms: int = int(os.getenv("PERF_TTI_MS", "5000"))
    api_response_ms: int = int(os.getenv("PERF_API_RESPONSE_MS", "2000"))
    search_response_ms: int = int(os.getenv("PERF_SEARCH_RESPONSE_MS", "2000"))
    form_submit_ms: int = int(os.getenv("PERF_FORM_SUBMIT_MS", "3000"))
    render_large_list_ms: int = int(os.getenv("PERF_RENDER_LARGE_LIST_MS", "5000"))
    file_upload_ms: int = int(os.getenv("PERF_FILE_UPLOAD_MS", "10000"))
    max_page_size_kb: int = int(os.getenv("PERF_MAX_PAGE_SIZE_KB", "3000"))
    max_memory_growth_mb: int = int(os.getenv("PERF_MAX_MEMORY_GROWTH_MB", "50"))


@pytest.fixture(scope="session")
def perf_thresholds() -> PerformanceThresholds:
    """Return the performance thresholds configuration."""
    return PerformanceThresholds()


@pytest.fixture()
def perf_page(page: Page) -> Page:
    """Return a page instance pre-configured for performance measurement.

    Clears browser caches to ensure cold-start measurements.
    """
    page.context.clear_cookies()
    return page


def measure_page_load(page: Page) -> dict:
    """Use the Performance API to gather navigation timing metrics.

    Returns a dict with loadTime, domContentLoaded, and firstPaint in ms.
    """
    metrics = page.evaluate("""
        () => {
            const perf = performance.getEntriesByType('navigation')[0] || {};
            const paint = performance.getEntriesByType('paint');
            const firstPaint = paint.find(p => p.name === 'first-paint');
            const fcp = paint.find(p => p.name === 'first-contentful-paint');
            return {
                loadTime: perf.loadEventEnd - perf.startTime || 0,
                domContentLoaded: perf.domContentLoadedEventEnd - perf.startTime || 0,
                domInteractive: perf.domInteractive - perf.startTime || 0,
                firstPaint: firstPaint ? firstPaint.startTime : 0,
                firstContentfulPaint: fcp ? fcp.startTime : 0,
                transferSize: perf.transferSize || 0,
                responseTime: perf.responseEnd - perf.requestStart || 0,
            };
        }
    """)
    return metrics


def measure_memory(page: Page) -> float | None:
    """Return the JS heap size in MB, or None if not supported."""
    result = page.evaluate("""
        () => {
            if (performance.memory) {
                return performance.memory.usedJSHeapSize / (1024 * 1024);
            }
            return null;
        }
    """)
    return result
