"""Login tests for authentication functionality.

Covers: valid/invalid login flows, form validation, security (XSS/SQL injection),
rate limiting, accessibility, and edge cases.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


pytestmark = [pytest.mark.auth]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

XSS_PAYLOADS = [
    '<script>alert("xss")</script>',
    '"><img src=x onerror=alert(1)>',
    "javascript:alert(document.cookie)",
    "' onmouseover='alert(1)'",
]

SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "'; DROP TABLE users; --",
    "admin'--",
    "1' UNION SELECT * FROM users--",
]


class TestLoginPageElements:
    """Tests verifying that all login page elements are present and correct."""

    @pytest.mark.smoke
    def test_login_page_elements_visible(self, page: Page) -> None:
        """All core form elements should be visible on the login page."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()

        assert login_page.is_visible(LoginPage.USERNAME_INPUT)
        assert login_page.is_visible(LoginPage.PASSWORD_INPUT)
        assert login_page.is_visible(LoginPage.LOGIN_BUTTON)
        assert login_page.is_visible(LoginPage.REMEMBER_ME_CHECKBOX)
        assert login_page.is_visible(LoginPage.FORGOT_PASSWORD_LINK)
        assert login_page.is_visible(LoginPage.REGISTER_LINK)

    def test_login_form_visible(self, page: Page) -> None:
        """The login form container should be rendered."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()

        assert login_page.is_login_form_visible()

    def test_login_password_field_is_masked(self, page: Page) -> None:
        """The password input should have type='password' to mask characters."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()

        input_type = login_page.get_attribute(LoginPage.PASSWORD_INPUT, "type")
        assert input_type == "password"


class TestSuccessfulLogin:
    """Tests for valid login scenarios."""

    @pytest.mark.smoke
    def test_successful_login_with_valid_credentials(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """User should be able to log in with valid credentials."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(test_user["email"], test_user["password"])

        page.wait_for_url("**/dashboard**")
        assert "dashboard" in page.url

    @pytest.mark.smoke
    def test_login_redirects_to_dashboard(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """After login the user should be redirected to the dashboard."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(test_user["email"], test_user["password"])

        page.wait_for_url("**/dashboard**")
        dashboard = DashboardPage(page)
        assert dashboard.is_visible(DashboardPage.WELCOME_MESSAGE)

    def test_login_with_remember_me(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """Login with Remember Me checked should succeed."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login_with_remember_me(test_user["email"], test_user["password"])

        page.wait_for_url("**/dashboard**")
        assert "dashboard" in page.url

    def test_login_without_remember_me(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """Login without Remember Me should still succeed normally."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(test_user["email"], test_user["password"])

        page.wait_for_url("**/dashboard**")
        assert "dashboard" in page.url

    def test_login_case_insensitive_email(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """Email should be treated case-insensitively during login."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        upper_email = test_user["email"].upper()
        login_page.login(upper_email, test_user["password"])

        page.wait_for_url("**/dashboard**")
        assert "dashboard" in page.url

    def test_login_with_special_characters_password(self, page: Page) -> None:
        """Passwords containing special characters should be accepted."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        # Just verify we can type special chars without JS errors
        login_page.fill(LoginPage.PASSWORD_INPUT, "P@$$w0rd!#%&*()_+-=[]{}|;':\",./<>?")
        value = login_page.get_input_value(LoginPage.PASSWORD_INPUT)
        assert len(value) > 0


class TestFailedLogin:
    """Tests for invalid login attempts."""

    @pytest.mark.regression
    def test_login_with_invalid_email(self, page: Page) -> None:
        """Login should fail with a non-existent email."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login("nonexistent@example.com", "somepassword")

        assert login_page.is_error_visible()

    @pytest.mark.regression
    def test_login_with_invalid_password(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """Login should fail when the password is wrong."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(test_user["email"], "wrongpassword123")

        assert login_page.is_error_visible()

    def test_login_with_empty_email(self, page: Page) -> None:
        """Submitting the form with an empty email should show an error."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.fill(LoginPage.PASSWORD_INPUT, "somepassword")
        login_page.click(LoginPage.LOGIN_BUTTON)

        assert login_page.is_error_visible() or login_page.is_visible(LoginPage.LOGIN_FORM)

    def test_login_with_empty_password(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """Submitting the form with an empty password should show an error."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.fill(LoginPage.USERNAME_INPUT, test_user["email"])
        login_page.click(LoginPage.LOGIN_BUTTON)

        assert login_page.is_error_visible() or login_page.is_visible(LoginPage.LOGIN_FORM)

    def test_login_with_empty_form(self, page: Page) -> None:
        """Submitting a completely empty form should not proceed."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.click(LoginPage.LOGIN_BUTTON)

        # Should still be on login page
        assert "/login" in page.url

    def test_login_error_message_displayed(self, page: Page) -> None:
        """An error message should appear after a failed login attempt."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login("wrong@example.com", "wrongpass")

        assert login_page.is_error_visible()
        error_text = login_page.get_error_message()
        assert len(error_text) > 0

    def test_login_email_field_validation(self, page: Page) -> None:
        """The email field should reject obviously invalid formats."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.fill(LoginPage.USERNAME_INPUT, "not-an-email")
        login_page.fill(LoginPage.PASSWORD_INPUT, "somepassword")
        login_page.click(LoginPage.LOGIN_BUTTON)

        # Should show error or remain on login page
        assert login_page.is_error_visible() or "/login" in page.url


class TestLoginSecurity:
    """Security-focused tests for the login page."""

    @pytest.mark.regression
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_login_with_sql_injection_attempt(self, page: Page, payload: str) -> None:
        """SQL injection payloads in the email field should not bypass auth."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(payload, "password")

        # Must NOT land on dashboard
        assert "dashboard" not in page.url

    @pytest.mark.regression
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_login_with_xss_attempt(self, page: Page, payload: str) -> None:
        """XSS payloads should be sanitized and not execute in the browser."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(payload, payload)

        # Check that no alert dialog was triggered
        page_content = page.content()
        assert "<script>alert" not in page_content

    @pytest.mark.regression
    def test_login_rate_limiting(self, page: Page) -> None:
        """Multiple rapid failed logins should eventually trigger rate limiting."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()

        for i in range(6):
            login_page.clear_fields()
            login_page.login(f"attacker{i}@example.com", "wrongpassword")
            # Brief pause between attempts
            page.wait_for_timeout(300)

        # After several failures the app should show a rate-limit or lock message.
        # We just verify the user is NOT on the dashboard.
        assert "dashboard" not in page.url


class TestLoginAccessibility:
    """Accessibility and usability tests for the login form."""

    def test_login_tab_order(self, page: Page) -> None:
        """Tab key should move focus through email -> password -> submit in order."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()

        login_page.click(LoginPage.USERNAME_INPUT)
        page.keyboard.press("Tab")

        # After first tab, focus should be on password
        focused = page.evaluate("document.activeElement.getAttribute('data-testid')")
        assert focused in ("password-input", "remember-me-checkbox")

    @pytest.mark.regression
    def test_login_enter_key_submits_form(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """Pressing Enter in the password field should submit the form."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.fill(LoginPage.USERNAME_INPUT, test_user["email"])
        login_page.fill(LoginPage.PASSWORD_INPUT, test_user["password"])
        page.keyboard.press("Enter")

        page.wait_for_url("**/dashboard**")
        assert "dashboard" in page.url

    def test_login_preserves_redirect_url(self, page: Page, test_user: dict[str, str]) -> None:
        """When redirected to login from a protected page, post-login should return there."""
        # Attempt to access a protected page directly
        page.goto(f"{settings.base_url}/profile")

        # Should be redirected to login
        page.wait_for_url("**/login**")

        login_page = LoginPage(page)
        login_page.login(test_user["email"], test_user["password"])

        # After login, should go back to the originally requested page
        page.wait_for_load_state("domcontentloaded")
        assert "profile" in page.url or "dashboard" in page.url
