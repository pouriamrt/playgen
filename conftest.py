from __future__ import annotations

import logging
from typing import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from config.settings import settings
from utils.api_client import APIClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Ensure artifact directories exist before any test runs."""
    settings.ensure_artifact_dirs()


# ---------------------------------------------------------------------------
# Browser context fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Override default browser context args with project settings."""
    return {
        **browser_context_args,
        "viewport": {
            "width": settings.viewport.width,
            "height": settings.viewport.height,
        },
        "record_video_dir": str(settings.videos_dir) if settings.video_recording != "off" else None,
        "base_url": settings.base_url,
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict) -> dict:
    """Override default browser launch args with project settings."""
    return {
        **browser_type_launch_args,
        "headless": settings.browser.headless,
        "slow_mo": settings.browser.slow_mo,
    }


# ---------------------------------------------------------------------------
# Page fixture with tracing support
# ---------------------------------------------------------------------------


@pytest.fixture()
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Create a new page with optional tracing."""
    if settings.trace_recording != "off":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    _page = context.new_page()
    _page.set_default_timeout(settings.default_timeout)

    yield _page

    _page.close()


# ---------------------------------------------------------------------------
# Auth state fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def authenticated_page(page: Page) -> Page:
    """Return a page that is logged in as the standard test user.

    Override this fixture in your test module if the login flow differs.
    """
    page.goto(f"{settings.base_url}/login")
    page.fill('[data-testid="username-input"]', settings.test_user)
    page.fill('[data-testid="password-input"]', settings.test_pass)
    page.click('[data-testid="login-button"]')
    page.wait_for_url("**/dashboard**")
    return page


@pytest.fixture()
def admin_page(page: Page) -> Page:
    """Return a page that is logged in as the admin user."""
    page.goto(f"{settings.base_url}/login")
    page.fill('[data-testid="username-input"]', settings.admin_user)
    page.fill('[data-testid="password-input"]', settings.admin_pass)
    page.click('[data-testid="login-button"]')
    page.wait_for_url("**/dashboard**")
    return page


@pytest.fixture()
def guest_page(page: Page) -> Page:
    """Return a page with no authentication (guest user)."""
    return page


# ---------------------------------------------------------------------------
# API client fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def api_client() -> Generator[APIClient, None, None]:
    """Provide an API client instance for backend verification."""
    client = APIClient()
    yield client
    client.session.close()


# ---------------------------------------------------------------------------
# Screenshot on failure
# ---------------------------------------------------------------------------


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Generator:
    """Capture a screenshot when a test fails."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed and settings.screenshot_on_failure:
        page: Page | None = item.funcargs.get("page") or item.funcargs.get("authenticated_page")
        if page and not page.is_closed():
            test_name = item.name.replace("[", "_").replace("]", "_").rstrip("_")
            screenshot_path = settings.screenshots_dir / f"FAIL_{test_name}.png"
            try:
                page.screenshot(path=str(screenshot_path))
                logger.info("Failure screenshot saved: %s", screenshot_path)
            except Exception as exc:
                logger.warning("Could not capture failure screenshot: %s", exc)

    # Save trace on failure
    if (
        report.when == "call"
        and report.failed
        and settings.trace_recording != "off"
    ):
        page = item.funcargs.get("page") or item.funcargs.get("authenticated_page")
        if page and not page.is_closed():
            test_name = item.name.replace("[", "_").replace("]", "_").rstrip("_")
            trace_path = settings.traces_dir / f"FAIL_{test_name}.zip"
            try:
                page.context.tracing.stop(path=str(trace_path))
                logger.info("Failure trace saved: %s", trace_path)
            except Exception as exc:
                logger.warning("Could not capture failure trace: %s", exc)


# ---------------------------------------------------------------------------
# Database cleanup fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_cleanup():
    """Provide a database helper that auto-disconnects after the test.

    Usage:
        def test_something(db_cleanup):
            db_cleanup.execute("DELETE FROM users WHERE email LIKE '%@test.example.com'")
    """
    from utils.database import DatabaseHelper

    db = DatabaseHelper()
    try:
        db.connect()
    except Exception:
        pytest.skip("Database not available")
    yield db
    db.disconnect()
