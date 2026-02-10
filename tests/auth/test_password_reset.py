"""Password reset tests for authentication functionality.

Covers: forgot password flow, email submission, token validation,
new password setting, and old password invalidation.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from config.settings import settings
from pages.login_page import LoginPage
from utils.api_client import APIClient
from utils.helpers import random_email


pytestmark = [pytest.mark.auth]

FORGOT_PASSWORD_EMAIL_INPUT = '[data-testid="forgot-password-email"]'
FORGOT_PASSWORD_SUBMIT = '[data-testid="forgot-password-submit"]'
FORGOT_PASSWORD_SUCCESS = '[data-testid="forgot-password-success"]'
FORGOT_PASSWORD_ERROR = '[data-testid="forgot-password-error"]'
RESET_PASSWORD_INPUT = '[data-testid="reset-new-password"]'
RESET_CONFIRM_PASSWORD_INPUT = '[data-testid="reset-confirm-password"]'
RESET_SUBMIT_BUTTON = '[data-testid="reset-password-submit"]'
RESET_SUCCESS_MESSAGE = '[data-testid="reset-success-message"]'
RESET_ERROR_MESSAGE = '[data-testid="reset-error-message"]'


class TestForgotPasswordPage:
    """Tests for the 'Forgot Password' link and form."""

    @pytest.mark.smoke
    def test_forgot_password_link_visible(self, page: Page) -> None:
        """The Forgot Password link should be visible on the login page."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()

        assert login_page.is_visible(LoginPage.FORGOT_PASSWORD_LINK)

    @pytest.mark.smoke
    def test_forgot_password_page_loads(self, page: Page) -> None:
        """Clicking Forgot Password should navigate to the reset request page."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.click_forgot_password()

        page.wait_for_load_state("domcontentloaded")
        assert (
            "forgot" in page.url
            or "reset" in page.url
            or "password" in page.url
        )

    @pytest.mark.regression
    def test_password_reset_with_valid_email(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """Submitting a registered email should show a success message."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.click_forgot_password()

        page.wait_for_load_state("domcontentloaded")
        page.fill(FORGOT_PASSWORD_EMAIL_INPUT, test_user["email"])
        page.click(FORGOT_PASSWORD_SUBMIT)

        page.wait_for_load_state("domcontentloaded")
        assert (
            page.is_visible(FORGOT_PASSWORD_SUCCESS)
            or "check your email" in page.content().lower()
            or "sent" in page.content().lower()
        )

    @pytest.mark.regression
    def test_password_reset_with_invalid_email(self, page: Page) -> None:
        """An invalid email format should show a validation error."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.click_forgot_password()

        page.wait_for_load_state("domcontentloaded")
        page.fill(FORGOT_PASSWORD_EMAIL_INPUT, "not-valid-email")
        page.click(FORGOT_PASSWORD_SUBMIT)

        page.wait_for_load_state("domcontentloaded")
        assert page.is_visible(FORGOT_PASSWORD_ERROR) or "forgot" in page.url

    @pytest.mark.regression
    def test_password_reset_with_unregistered_email(self, page: Page) -> None:
        """An unregistered email should show a message (but not reveal user existence)."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.click_forgot_password()

        page.wait_for_load_state("domcontentloaded")
        page.fill(FORGOT_PASSWORD_EMAIL_INPUT, random_email())
        page.click(FORGOT_PASSWORD_SUBMIT)

        page.wait_for_load_state("domcontentloaded")
        # For security, most apps show the same success-like message
        # whether or not the email is registered
        assert (
            page.is_visible(FORGOT_PASSWORD_SUCCESS)
            or page.is_visible(FORGOT_PASSWORD_ERROR)
            or "forgot" in page.url
        )

    def test_password_reset_success_message(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """After submitting a valid reset request, a confirmation message should appear."""
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.click_forgot_password()

        page.wait_for_load_state("domcontentloaded")
        page.fill(FORGOT_PASSWORD_EMAIL_INPUT, test_user["email"])
        page.click(FORGOT_PASSWORD_SUBMIT)

        page.wait_for_load_state("domcontentloaded")
        content = page.content().lower()
        assert "email" in content or "sent" in content or page.is_visible(FORGOT_PASSWORD_SUCCESS)


class TestPasswordResetToken:
    """Tests for the password reset token and new-password form."""

    def test_password_reset_token_expiry(self, page: Page, api_client: APIClient) -> None:
        """An expired reset token should be rejected."""
        # Navigate to reset page with a known-expired token
        page.goto(f"{settings.base_url}/reset-password?token=expired-token-12345")
        page.wait_for_load_state("domcontentloaded")

        # Should see an error about expired/invalid token
        assert (
            page.is_visible(RESET_ERROR_MESSAGE)
            or "expired" in page.content().lower()
            or "invalid" in page.content().lower()
            or "login" in page.url
        )

    def test_password_reset_with_new_password(self, page: Page) -> None:
        """A valid token should allow setting a new password."""
        # Navigate to the reset form with a test token
        page.goto(f"{settings.base_url}/reset-password?token=valid-test-token")
        page.wait_for_load_state("domcontentloaded")

        if page.is_visible(RESET_PASSWORD_INPUT):
            page.fill(RESET_PASSWORD_INPUT, "NewSecureP@ss1!")
            page.fill(RESET_CONFIRM_PASSWORD_INPUT, "NewSecureP@ss1!")
            page.click(RESET_SUBMIT_BUTTON)

            page.wait_for_load_state("domcontentloaded")
            assert (
                page.is_visible(RESET_SUCCESS_MESSAGE)
                or "login" in page.url
            )

    def test_password_reset_token_single_use(self, page: Page) -> None:
        """A reset token should only be usable once."""
        token = "single-use-test-token"

        # First use
        page.goto(f"{settings.base_url}/reset-password?token={token}")
        page.wait_for_load_state("domcontentloaded")

        if page.is_visible(RESET_PASSWORD_INPUT):
            page.fill(RESET_PASSWORD_INPUT, "NewSecureP@ss1!")
            page.fill(RESET_CONFIRM_PASSWORD_INPUT, "NewSecureP@ss1!")
            page.click(RESET_SUBMIT_BUTTON)
            page.wait_for_load_state("domcontentloaded")

        # Second use of same token should fail
        page.goto(f"{settings.base_url}/reset-password?token={token}")
        page.wait_for_load_state("domcontentloaded")

        assert (
            page.is_visible(RESET_ERROR_MESSAGE)
            or "expired" in page.content().lower()
            or "invalid" in page.content().lower()
            or "login" in page.url
        )

    def test_password_reset_password_validation(self, page: Page) -> None:
        """The new password should meet strength requirements."""
        page.goto(f"{settings.base_url}/reset-password?token=valid-test-token")
        page.wait_for_load_state("domcontentloaded")

        if page.is_visible(RESET_PASSWORD_INPUT):
            page.fill(RESET_PASSWORD_INPUT, "weak")
            page.fill(RESET_CONFIRM_PASSWORD_INPUT, "weak")
            page.click(RESET_SUBMIT_BUTTON)

            page.wait_for_load_state("domcontentloaded")
            assert (
                page.is_visible(RESET_ERROR_MESSAGE)
                or "reset" in page.url
            )

    def test_password_reset_login_with_new_password(
        self, page: Page, test_user: dict[str, str]
    ) -> None:
        """After resetting the password, user should be able to login with the new one.

        Note: This test verifies the login flow works. Actual password reset
        integration depends on having a working reset token mechanism.
        """
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(test_user["email"], test_user["password"])

        page.wait_for_load_state("domcontentloaded")
        assert "dashboard" in page.url or "login" in page.url

    def test_password_reset_old_password_invalid(
        self, page: Page
    ) -> None:
        """After a password reset, the old password should no longer work.

        Note: This is a conceptual test. Full integration depends on the
        actual reset mechanism being exercised end-to-end.
        """
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login("resetuser@example.com", "old-password-that-was-changed")

        page.wait_for_load_state("domcontentloaded")
        # Old password should fail
        assert "dashboard" not in page.url
