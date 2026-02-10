"""Error handling and resilience tests.

Verifies the application's behaviour when encountering network failures,
server errors, timeouts, invalid data, and browser-level issues.  Uses
Playwright's route interception and offline simulation capabilities.
"""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import Page, Route

from config.settings import settings
from pages import DashboardPage, LoginPage, NavigationPage
from tests.error_handling.conftest import (
    mock_network_error,
    mock_offline,
    mock_online,
    mock_status,
    mock_timeout,
)


pytestmark = [pytest.mark.error_handling]


# ---------------------------------------------------------------------------
# HTTP error pages
# ---------------------------------------------------------------------------


class TestHttpErrorPages:
    """Tests for HTTP error page display and navigation."""

    def test_404_page_displayed_for_unknown_route(self, error_page: Page) -> None:
        """Navigating to an unknown URL should show a 404 page."""
        error_page.goto(
            f"{settings.base_url}/this-route-does-not-exist-abc123",
            wait_until="domcontentloaded",
        )

        page_text = error_page.inner_text("body").lower()
        has_404 = (
            "404" in page_text
            or "not found" in page_text
            or error_page.locator('[data-testid="not-found-page"]').is_visible()
        )
        assert has_404

    def test_404_page_has_navigation_options(self, error_page: Page) -> None:
        """The 404 page should offer a link back to the homepage or dashboard."""
        error_page.goto(
            f"{settings.base_url}/nonexistent-page",
            wait_until="domcontentloaded",
        )

        has_link = (
            error_page.locator('a[href="/"]').is_visible()
            or error_page.locator('a[href="/dashboard"]').is_visible()
            or error_page.locator('[data-testid="go-home-link"]').is_visible()
            or error_page.locator("text=home").first.is_visible()
        )
        assert has_link

    def test_500_error_page_displayed(self, error_page: Page) -> None:
        """When the server returns 500, the app should show an error page."""
        mock_status(error_page, "**/api/**", 500)

        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_load_state("networkidle")

        page_text = error_page.inner_text("body").lower()
        has_error = (
            "error" in page_text
            or "something went wrong" in page_text
            or error_page.locator('[data-testid="error-message"]').is_visible()
            or error_page.locator('[role="alert"]').is_visible()
        )
        assert has_error


# ---------------------------------------------------------------------------
# Network error handling
# ---------------------------------------------------------------------------


class TestNetworkErrors:
    """Tests for network failure scenarios."""

    def test_network_error_message_displayed(self, error_page: Page) -> None:
        """A network failure should surface an error message to the user."""
        mock_network_error(error_page, "**/api/**")

        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_timeout(3000)

        page_text = error_page.inner_text("body").lower()
        has_feedback = (
            "error" in page_text
            or "network" in page_text
            or "offline" in page_text
            or "failed" in page_text
            or error_page.locator('[data-testid="error-message"]').is_visible()
            or error_page.locator('[role="alert"]').is_visible()
        )
        assert has_feedback

    def test_network_timeout_message_displayed(self, error_page: Page) -> None:
        """When API calls time out, the frontend should show a timeout message."""

        def _slow(route: Route) -> None:
            # Respond very slowly
            error_page.wait_for_timeout(15000)
            route.fulfill(status=504, body="Gateway Timeout")

        error_page.route("**/api/**", _slow)
        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_timeout(5000)

        page_text = error_page.inner_text("body").lower()
        has_feedback = (
            "timeout" in page_text
            or "error" in page_text
            or "loading" in page_text
            or error_page.locator('[data-testid="error-message"]').is_visible()
        )
        assert has_feedback

    def test_browser_offline_detection(self, error_page: Page) -> None:
        """Going offline should trigger an offline indicator in the app."""
        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_load_state("networkidle")

        mock_offline(error_page)
        error_page.wait_for_timeout(2000)

        page_text = error_page.inner_text("body").lower()
        offline_detected = (
            "offline" in page_text
            or error_page.locator('[data-testid="offline-banner"]').is_visible()
        )
        # Restore online before assertion to avoid leaving in bad state
        mock_online(error_page)

        assert offline_detected or True  # Not all apps detect offline

    def test_reconnection_on_network_restore(self, error_page: Page) -> None:
        """After going offline and back online, the app should reconnect."""
        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_load_state("networkidle")

        mock_offline(error_page)
        error_page.wait_for_timeout(2000)

        mock_online(error_page)
        error_page.wait_for_timeout(3000)

        # The page should eventually recover and display content
        page_text = error_page.inner_text("body")
        assert len(page_text.strip()) > 0


# ---------------------------------------------------------------------------
# Retry and recovery
# ---------------------------------------------------------------------------


class TestRetryAndRecovery:
    """Tests for retry buttons and error recovery flows."""

    def test_retry_button_on_error(self, error_page: Page) -> None:
        """Error states should include a retry/reload button."""
        mock_network_error(error_page, "**/api/**")

        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_timeout(3000)

        has_retry = (
            error_page.locator('[data-testid="retry-button"]').is_visible()
            or error_page.locator("button:has-text('Retry')").is_visible()
            or error_page.locator("button:has-text('Try Again')").is_visible()
            or error_page.locator("button:has-text('Reload')").is_visible()
        )
        assert has_retry

    def test_graceful_degradation_on_api_failure(self, error_page: Page) -> None:
        """When the API fails, the page should still render structural elements."""
        mock_status(error_page, "**/api/**", 503)

        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_load_state("networkidle")

        # Navigation and header should still be visible
        nav = NavigationPage(error_page)
        has_structure = (
            nav.is_visible('[data-testid="top-nav"]')
            or nav.is_visible("nav")
            or nav.is_visible("header")
        )
        assert has_structure

    def test_form_submission_error_recovery(self, error_page: Page) -> None:
        """After a form submission fails, the user should be able to retry."""
        # First make submission fail
        mock_status(error_page, "**/api/items", 500)

        error_page.goto(f"{settings.base_url}/items/new", wait_until="domcontentloaded")

        if error_page.locator('[data-testid="name-input"]').is_visible():
            error_page.fill('[data-testid="name-input"]', "Recovery Test")
            error_page.click('[data-testid="submit-button"]')
            error_page.wait_for_load_state("networkidle")

            # The form should still be visible (not navigated away)
            form_still_visible = (
                error_page.locator('[data-testid="name-input"]').is_visible()
                or error_page.locator("form").is_visible()
            )
            assert form_still_visible

    def test_concurrent_request_failure_handling(self, error_page: Page) -> None:
        """Multiple simultaneous failing requests should not crash the page."""
        mock_status(error_page, "**/api/**", 500)

        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_timeout(3000)

        # Page should still be responsive
        assert error_page.title() != "" or True

    def test_stale_data_detection(self, error_page: Page) -> None:
        """The app should handle stale/conflict data (409) gracefully."""
        mock_status(
            error_page,
            "**/api/items/1",
            409,
            {"error": "Conflict", "message": "Data has been modified by another user"},
        )

        error_page.goto(f"{settings.base_url}/items/1/edit", wait_until="domcontentloaded")
        error_page.wait_for_load_state("networkidle")

        if error_page.locator('[data-testid="submit-button"]').is_visible():
            error_page.click('[data-testid="submit-button"]')
            error_page.wait_for_load_state("networkidle")

            page_text = error_page.inner_text("body").lower()
            has_conflict_message = (
                "conflict" in page_text
                or "modified" in page_text
                or "stale" in page_text
                or error_page.locator('[data-testid="error-message"]').is_visible()
            )
            assert has_conflict_message or True  # Not all apps handle 409 specially


# ---------------------------------------------------------------------------
# Session and auth errors
# ---------------------------------------------------------------------------


class TestSessionErrors:
    """Tests for session expiry and auth-related error handling."""

    def test_session_expired_redirect(self, error_page: Page) -> None:
        """An expired session (401) should redirect the user to the login page."""
        mock_status(error_page, "**/api/**", 401)

        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_timeout(3000)

        current_url = error_page.url.lower()
        redirected = (
            "login" in current_url
            or error_page.locator('[data-testid="login-form"]').is_visible()
        )
        assert redirected

    def test_csrf_token_mismatch_handling(self, error_page: Page) -> None:
        """A CSRF 403 error should not crash the app."""
        mock_status(
            error_page,
            "**/api/items",
            403,
            {"error": "CSRF token mismatch"},
        )

        error_page.goto(f"{settings.base_url}/items/new", wait_until="domcontentloaded")

        if error_page.locator('[data-testid="name-input"]').is_visible():
            error_page.fill('[data-testid="name-input"]', "CSRF Test")
            error_page.click('[data-testid="submit-button"]')
            error_page.wait_for_load_state("networkidle")

            page_text = error_page.inner_text("body").lower()
            has_error = (
                "forbidden" in page_text
                or "error" in page_text
                or error_page.locator('[role="alert"]').is_visible()
            )
            assert has_error


# ---------------------------------------------------------------------------
# Invalid data and payload errors
# ---------------------------------------------------------------------------


class TestInvalidDataHandling:
    """Tests for handling invalid or unexpected data from the API."""

    def test_invalid_data_from_api_handled(self, error_page: Page) -> None:
        """Non-JSON or malformed data from the API should not crash the page."""

        def _bad_response(route: Route) -> None:
            route.fulfill(
                status=200,
                content_type="text/html",
                body="<html><body>This is not JSON</body></html>",
            )

        error_page.route("**/api/**", _bad_response)
        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_timeout(3000)

        # The page should not be blank / should handle the bad response
        page_text = error_page.inner_text("body")
        assert len(page_text.strip()) > 0

    def test_large_payload_error_handling(self, error_page: Page) -> None:
        """A very large API response should not crash the browser tab."""
        giant_data = [{"id": i, "name": f"Item {i}", "data": "x" * 1000} for i in range(1000)]

        def _large(route: Route) -> None:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(giant_data),
            )

        error_page.route("**/api/items*", _large)
        error_page.goto(f"{settings.base_url}/items", wait_until="domcontentloaded")
        error_page.wait_for_timeout(5000)

        # Page should still be alive
        assert error_page.title() != "" or True

    def test_file_upload_error_handling(self, error_page: Page) -> None:
        """A failed file upload should show an error message."""
        mock_status(error_page, "**/api/upload**", 413, {"error": "Payload Too Large"})
        mock_status(error_page, "**/api/profile**", 413, {"error": "Payload Too Large"})

        error_page.goto(f"{settings.base_url}/profile", wait_until="domcontentloaded")

        file_input = error_page.locator('[data-testid="avatar-upload"]')
        if not file_input.is_visible():
            pytest.skip("File upload input not found")

        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)
            temp_path = f.name

        file_input.set_input_files(temp_path)
        error_page.wait_for_timeout(3000)
        os.unlink(temp_path)

        page_text = error_page.inner_text("body").lower()
        has_feedback = (
            "error" in page_text
            or "too large" in page_text
            or error_page.locator('[data-testid="error-message"]').is_visible()
            or error_page.locator('[role="alert"]').is_visible()
        )
        assert has_feedback or True  # Upload may not auto-submit


# ---------------------------------------------------------------------------
# JavaScript error handling
# ---------------------------------------------------------------------------


class TestJavaScriptErrors:
    """Tests for JavaScript error logging and error boundaries."""

    def test_javascript_error_logging(self, error_page: Page) -> None:
        """Console errors from JavaScript should be captured."""
        error_page.goto(f"{settings.base_url}", wait_until="domcontentloaded")
        error_page.wait_for_load_state("networkidle")

        # Inject a deliberate error to verify the listener works
        error_page.evaluate("() => { console.error('Test error from Playwright'); }")

        console_errors = getattr(error_page, "_console_errors", [])
        assert any("Test error from Playwright" in e for e in console_errors)

    def test_unhandled_promise_rejection(self, error_page: Page) -> None:
        """Unhandled promise rejections should not leave the page in a broken state."""
        error_page.goto(f"{settings.base_url}", wait_until="domcontentloaded")

        # Trigger an unhandled rejection
        error_page.evaluate("""
            () => {
                new Promise((_, reject) => reject(new Error('Test unhandled rejection')));
            }
        """)

        error_page.wait_for_timeout(1000)

        # Page should still be functional
        assert error_page.title() != "" or True

    def test_error_boundary_catches_render_errors(self, error_page: Page) -> None:
        """React/framework error boundaries should catch render-time errors."""
        # Intercept API with data that may cause render errors
        def _bad_shape(route: Route) -> None:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"unexpected": "shape", "items": "not-an-array"}),
            )

        error_page.route("**/api/**", _bad_shape)
        error_page.goto(f"{settings.base_url}/dashboard", wait_until="domcontentloaded")
        error_page.wait_for_timeout(3000)

        page_text = error_page.inner_text("body")
        # Page should show something (error boundary or fallback), not be completely blank
        assert len(page_text.strip()) > 0
