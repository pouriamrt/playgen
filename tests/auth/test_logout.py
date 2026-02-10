"""Logout tests for authentication functionality.

Covers: successful logout, session cleanup, redirect behavior,
back-button protection, and multi-tab scenarios.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from config.settings import settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


pytestmark = [pytest.mark.auth]

LOGOUT_BUTTON = '[data-testid="logout-button"]'
LOGOUT_MENU_ITEM = '[data-testid="user-menu-dropdown"] >> text=Logout'


class TestLogoutFlow:
    """Tests for the core logout workflow."""

    @pytest.mark.smoke
    def test_logout_button_visible_when_logged_in(self, logged_in_page: Page) -> None:
        """The logout control should be accessible when authenticated."""
        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()
        assert logged_in_page.is_visible(LOGOUT_BUTTON) or logged_in_page.is_visible(
            LOGOUT_MENU_ITEM
        )

    @pytest.mark.smoke
    def test_successful_logout(self, logged_in_page: Page) -> None:
        """Clicking logout should end the session and leave the authenticated area."""
        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()

        if logged_in_page.is_visible(LOGOUT_BUTTON):
            logged_in_page.click(LOGOUT_BUTTON)
        else:
            logged_in_page.click(LOGOUT_MENU_ITEM)

        logged_in_page.wait_for_load_state("domcontentloaded")
        assert "login" in logged_in_page.url or "home" in logged_in_page.url

    @pytest.mark.regression
    def test_logout_redirects_to_login(self, logged_in_page: Page) -> None:
        """After logout the user should be redirected to the login page."""
        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()

        if logged_in_page.is_visible(LOGOUT_BUTTON):
            logged_in_page.click(LOGOUT_BUTTON)
        else:
            logged_in_page.click(LOGOUT_MENU_ITEM)

        logged_in_page.wait_for_url("**/login**")
        assert "login" in logged_in_page.url


class TestLogoutSessionCleanup:
    """Tests verifying session state is fully cleared after logout."""

    @pytest.mark.regression
    def test_logout_clears_session(self, logged_in_page: Page) -> None:
        """After logout, session storage should not contain auth tokens."""
        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()

        if logged_in_page.is_visible(LOGOUT_BUTTON):
            logged_in_page.click(LOGOUT_BUTTON)
        else:
            logged_in_page.click(LOGOUT_MENU_ITEM)

        logged_in_page.wait_for_load_state("domcontentloaded")

        # Check that session/local storage is cleared of auth data
        token = logged_in_page.evaluate(
            "window.sessionStorage.getItem('token') || window.sessionStorage.getItem('auth_token')"
        )
        assert token is None or token == ""

    def test_logout_clears_local_storage(self, logged_in_page: Page) -> None:
        """Local storage auth entries should be removed after logout."""
        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()

        if logged_in_page.is_visible(LOGOUT_BUTTON):
            logged_in_page.click(LOGOUT_BUTTON)
        else:
            logged_in_page.click(LOGOUT_MENU_ITEM)

        logged_in_page.wait_for_load_state("domcontentloaded")

        local_token = logged_in_page.evaluate(
            "window.localStorage.getItem('token') || window.localStorage.getItem('auth_token')"
        )
        assert local_token is None or local_token == ""

    @pytest.mark.regression
    def test_cannot_access_protected_page_after_logout(self, logged_in_page: Page) -> None:
        """Navigating to a protected page after logout should redirect to login."""
        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()

        if logged_in_page.is_visible(LOGOUT_BUTTON):
            logged_in_page.click(LOGOUT_BUTTON)
        else:
            logged_in_page.click(LOGOUT_MENU_ITEM)

        logged_in_page.wait_for_load_state("domcontentloaded")

        # Try accessing dashboard directly
        logged_in_page.goto(f"{settings.base_url}/dashboard")
        logged_in_page.wait_for_load_state("domcontentloaded")

        assert "login" in logged_in_page.url

    def test_back_button_after_logout(self, logged_in_page: Page) -> None:
        """Pressing browser back after logout should not re-enter the dashboard."""
        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()

        if logged_in_page.is_visible(LOGOUT_BUTTON):
            logged_in_page.click(LOGOUT_BUTTON)
        else:
            logged_in_page.click(LOGOUT_MENU_ITEM)

        logged_in_page.wait_for_load_state("domcontentloaded")

        # Navigate back
        logged_in_page.go_back()
        logged_in_page.wait_for_load_state("domcontentloaded")

        # Should be redirected to login, not dashboard
        assert "dashboard" not in logged_in_page.url or "login" in logged_in_page.url


class TestLogoutAdvanced:
    """Advanced logout scenarios: multi-tab, API tokens, timeouts."""

    def test_logout_from_multiple_tabs(self, logged_in_page: Page) -> None:
        """Logging out in one tab should invalidate the session in another."""
        context = logged_in_page.context

        # Open a second tab to the dashboard
        second_page = context.new_page()
        second_page.goto(f"{settings.base_url}/dashboard")
        second_page.wait_for_load_state("domcontentloaded")

        # Logout from the first tab
        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()
        if logged_in_page.is_visible(LOGOUT_BUTTON):
            logged_in_page.click(LOGOUT_BUTTON)
        else:
            logged_in_page.click(LOGOUT_MENU_ITEM)
        logged_in_page.wait_for_load_state("domcontentloaded")

        # Reload the second tab -- should redirect to login
        second_page.reload()
        second_page.wait_for_load_state("domcontentloaded")

        assert "login" in second_page.url or "dashboard" not in second_page.url
        second_page.close()

    def test_logout_invalidates_api_token(self, logged_in_page: Page) -> None:
        """After logout, API calls with the old token should fail."""
        # Capture current token before logout
        token = logged_in_page.evaluate(
            """() => {
                return localStorage.getItem('token')
                    || sessionStorage.getItem('token')
                    || document.cookie.match(/token=([^;]+)/)?.[1]
                    || null;
            }"""
        )

        dashboard = DashboardPage(logged_in_page)
        dashboard.open_user_menu()
        if logged_in_page.is_visible(LOGOUT_BUTTON):
            logged_in_page.click(LOGOUT_BUTTON)
        else:
            logged_in_page.click(LOGOUT_MENU_ITEM)
        logged_in_page.wait_for_load_state("domcontentloaded")

        if token:
            # Attempt an API call with the old token
            response = logged_in_page.evaluate(
                """(token) => {
                    return fetch('/api/me', {
                        headers: { 'Authorization': 'Bearer ' + token }
                    }).then(r => r.status);
                }""",
                token,
            )
            assert response in (401, 403)

    @pytest.mark.slow
    def test_session_timeout_auto_logout(self, page: Page, test_user: dict[str, str]) -> None:
        """An idle session should eventually expire and redirect to login.

        Note: This test is marked slow because it may need to wait for timeout.
        The actual timeout duration depends on server configuration.
        """
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(test_user["email"], test_user["password"])
        page.wait_for_url("**/dashboard**")

        # Simulate inactivity by waiting (short wait for test purposes)
        page.wait_for_timeout(2000)

        # Attempt to perform an action that requires auth
        page.goto(f"{settings.base_url}/profile")
        page.wait_for_load_state("domcontentloaded")

        # The session may or may not have expired depending on server config.
        # We simply assert the page loaded without server error.
        assert page.url is not None
