from __future__ import annotations

import json
from typing import Any

import pytest
from playwright.sync_api import Page, Route


@pytest.fixture()
def error_page(page: Page) -> Page:
    """Return a page instance set up for error-handling tests.

    Attaches listeners that capture console errors and uncaught exceptions.
    """
    page._console_errors: list[str] = []  # type: ignore[attr-defined]
    page._js_exceptions: list[str] = []  # type: ignore[attr-defined]

    page.on("console", lambda msg: (
        page._console_errors.append(msg.text)  # type: ignore[attr-defined]
        if msg.type == "error" else None
    ))
    page.on("pageerror", lambda err: (
        page._js_exceptions.append(str(err))  # type: ignore[attr-defined]
    ))

    return page


def mock_network_error(page: Page, url_pattern: str) -> None:
    """Abort all matching requests to simulate a network failure."""

    def _abort(route: Route) -> None:
        route.abort("failed")

    page.route(url_pattern, _abort)


def mock_timeout(page: Page, url_pattern: str, delay_ms: int = 30000) -> None:
    """Delay matching requests to simulate a timeout."""

    def _delay(route: Route) -> None:
        page.wait_for_timeout(delay_ms)
        route.fulfill(status=504, body="Gateway Timeout")

    page.route(url_pattern, _delay)


def mock_status(
    page: Page,
    url_pattern: str,
    status: int,
    body: Any = None,
) -> None:
    """Return a specific HTTP status for matching requests."""

    def _handler(route: Route) -> None:
        route.fulfill(
            status=status,
            content_type="application/json",
            body=json.dumps(body or {"error": f"Simulated {status}"}),
        )

    page.route(url_pattern, _handler)


def mock_offline(page: Page) -> None:
    """Simulate the browser going offline by setting the context offline."""
    page.context.set_offline(True)


def mock_online(page: Page) -> None:
    """Restore the browser to online mode."""
    page.context.set_offline(False)
