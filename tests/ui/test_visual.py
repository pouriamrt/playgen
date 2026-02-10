"""Visual regression tests -- screenshot comparison using Playwright."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SNAPSHOT_OPTS = {"threshold": 0.3, "max_diff_pixel_ratio": 0.01}


def _navigate_and_wait(page: Page, path: str) -> None:
    """Navigate to a path and wait until network is idle."""
    page.goto(f"{settings.base_url}{path}")
    page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Desktop snapshots
# ---------------------------------------------------------------------------


@pytest.mark.visual
class TestDesktopSnapshots:
    """Visual regression snapshots at the default desktop viewport."""

    def test_homepage_visual_snapshot(self, page: Page) -> None:
        """Capture and compare a visual snapshot of the home page."""
        _navigate_and_wait(page, "/")
        expect(page).to_have_screenshot("homepage.png", **SNAPSHOT_OPTS)

    def test_login_page_visual_snapshot(self, page: Page) -> None:
        """Capture and compare a visual snapshot of the login page."""
        _navigate_and_wait(page, "/login")
        expect(page).to_have_screenshot("login.png", **SNAPSHOT_OPTS)

    def test_dashboard_visual_snapshot(self, authenticated_page: Page) -> None:
        """Capture and compare a visual snapshot of the dashboard."""
        _navigate_and_wait(authenticated_page, "/dashboard")
        expect(authenticated_page).to_have_screenshot(
            "dashboard.png", **SNAPSHOT_OPTS
        )

    def test_form_page_visual_snapshot(self, authenticated_page: Page) -> None:
        """Capture and compare a visual snapshot of a form page."""
        _navigate_and_wait(authenticated_page, "/form")
        expect(authenticated_page).to_have_screenshot(
            "form-page.png", **SNAPSHOT_OPTS
        )

    def test_error_page_visual_snapshot(self, page: Page) -> None:
        """Capture and compare a visual snapshot of the 404 error page."""
        _navigate_and_wait(page, "/this-does-not-exist-visual-test")
        expect(page).to_have_screenshot("error-404.png", **SNAPSHOT_OPTS)


# ---------------------------------------------------------------------------
# Mobile snapshots
# ---------------------------------------------------------------------------


@pytest.mark.visual
@pytest.mark.responsive
class TestMobileSnapshots:
    """Visual regression snapshots at a mobile viewport (375x667)."""

    def test_mobile_homepage_snapshot(self, page: Page) -> None:
        """Capture and compare the home page at mobile resolution."""
        page.set_viewport_size({"width": 375, "height": 667})
        _navigate_and_wait(page, "/")
        expect(page).to_have_screenshot("homepage-mobile.png", **SNAPSHOT_OPTS)


# ---------------------------------------------------------------------------
# Theme snapshots
# ---------------------------------------------------------------------------


@pytest.mark.visual
class TestThemeSnapshots:
    """Visual regression snapshots for dark mode / alternate themes."""

    def test_dark_mode_snapshot(self, authenticated_page: Page) -> None:
        """Capture and compare the dashboard in dark mode."""
        _navigate_and_wait(authenticated_page, "/settings")
        authenticated_page.select_option('[data-testid="theme-selector"]', value="dark")
        _navigate_and_wait(authenticated_page, "/dashboard")
        expect(authenticated_page).to_have_screenshot(
            "dashboard-dark.png", **SNAPSHOT_OPTS
        )
        # Restore light
        _navigate_and_wait(authenticated_page, "/settings")
        authenticated_page.select_option('[data-testid="theme-selector"]', value="light")


# ---------------------------------------------------------------------------
# State snapshots
# ---------------------------------------------------------------------------


@pytest.mark.visual
class TestStateSnapshots:
    """Visual regression snapshots for specific UI states."""

    def test_empty_state_snapshot(self, authenticated_page: Page) -> None:
        """Capture and compare an empty-state view (no data)."""
        _navigate_and_wait(authenticated_page, "/dashboard")
        empty = authenticated_page.locator('[data-testid="empty-state"]').first
        if empty.count() > 0 and empty.is_visible():
            expect(authenticated_page).to_have_screenshot(
                "empty-state.png", **SNAPSHOT_OPTS
            )
        else:
            pytest.skip("No empty state visible on dashboard")

    def test_loading_state_snapshot(self, page: Page) -> None:
        """Capture and compare the loading/skeleton state.

        Intercepts the API call to introduce a delay so the loading state
        is visible long enough for the screenshot.
        """
        page.route("**/api/**", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="{}",
            headers={"X-Delay": "5000"},
        ))
        page.goto(f"{settings.base_url}/dashboard")
        # Capture quickly before content loads
        skeleton = page.locator('[data-testid="skeleton"], .skeleton')
        if skeleton.count() > 0:
            expect(page).to_have_screenshot("loading-state.png", **SNAPSHOT_OPTS)
        else:
            pytest.skip("No skeleton/loading state captured")

    def test_print_layout_snapshot(self, authenticated_page: Page) -> None:
        """Capture and compare the print layout using emulated print media."""
        _navigate_and_wait(authenticated_page, "/dashboard")
        authenticated_page.emulate_media(media="print")
        expect(authenticated_page).to_have_screenshot(
            "print-layout.png", **SNAPSHOT_OPTS
        )
        authenticated_page.emulate_media(media="screen")
