from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from pages.base_page import BasePage


class RegisterPage(BasePage):
    """Page Object for the Registration / Sign-up page."""

    # Selectors
    FIRST_NAME_INPUT = '[data-testid="first-name-input"]'
    LAST_NAME_INPUT = '[data-testid="last-name-input"]'
    EMAIL_INPUT = '[data-testid="email-input"]'
    PASSWORD_INPUT = '[data-testid="password-input"]'
    CONFIRM_PASSWORD_INPUT = '[data-testid="confirm-password-input"]'
    TERMS_CHECKBOX = '[data-testid="terms-checkbox"]'
    REGISTER_BUTTON = '[data-testid="register-button"]'
    SUCCESS_MESSAGE = '[data-testid="success-message"]'
    PASSWORD_STRENGTH = '[data-testid="password-strength"]'
    REGISTER_FORM = '[data-testid="register-form"]'

    # Dynamic selector for per-field errors
    FIELD_ERROR_TEMPLATE = '[data-testid="{field}-error"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.path = "/register"

    def navigate_to_register(self) -> None:
        """Navigate to the registration page."""
        self.navigate(self.path)

    def fill_registration_form(
        self,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        password: str = "",
        confirm_password: str = "",
    ) -> None:
        """Fill all registration form fields."""
        if first_name:
            self.fill(self.FIRST_NAME_INPUT, first_name)
        if last_name:
            self.fill(self.LAST_NAME_INPUT, last_name)
        if email:
            self.fill(self.EMAIL_INPUT, email)
        if password:
            self.fill(self.PASSWORD_INPUT, password)
        if confirm_password:
            self.fill(self.CONFIRM_PASSWORD_INPUT, confirm_password)

    def register(self, user_data: dict[str, str]) -> None:
        """Fill the form from a dict and submit."""
        self.fill_registration_form(
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
            email=user_data.get("email", ""),
            password=user_data.get("password", ""),
            confirm_password=user_data.get("confirm_password", user_data.get("password", "")),
        )
        self.accept_terms()
        self.submit()

    def accept_terms(self) -> None:
        """Check the terms and conditions checkbox."""
        self.check(self.TERMS_CHECKBOX)

    def submit(self) -> None:
        """Click the register button."""
        self.click(self.REGISTER_BUTTON)

    def get_field_error(self, field: str) -> str:
        """Return the validation error message for a specific field."""
        selector = self.FIELD_ERROR_TEMPLATE.format(field=field)
        return self.get_text(selector)

    def is_field_error_visible(self, field: str) -> bool:
        """Check if a validation error is visible for a specific field."""
        selector = self.FIELD_ERROR_TEMPLATE.format(field=field)
        return self.is_visible(selector)

    def get_success_message(self) -> str:
        """Return the text of the success message."""
        return self.get_text(self.SUCCESS_MESSAGE)

    def is_password_strength_shown(self) -> bool:
        """Check whether the password strength indicator is visible."""
        return self.is_visible(self.PASSWORD_STRENGTH)
