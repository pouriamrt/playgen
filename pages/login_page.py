from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class LoginPage(BasePage):
    """Page Object for the Login page."""

    # Selectors
    USERNAME_INPUT = '[data-testid="username-input"]'
    PASSWORD_INPUT = '[data-testid="password-input"]'
    LOGIN_BUTTON = '[data-testid="login-button"]'
    REMEMBER_ME_CHECKBOX = '[data-testid="remember-me-checkbox"]'
    FORGOT_PASSWORD_LINK = '[data-testid="forgot-password-link"]'
    REGISTER_LINK = '[data-testid="register-link"]'
    ERROR_MESSAGE = '[data-testid="error-message"]'
    SUCCESS_MESSAGE = '[data-testid="success-message"]'
    SOCIAL_LOGIN_GOOGLE = '[data-testid="social-login-google"]'
    SOCIAL_LOGIN_GITHUB = '[data-testid="social-login-github"]'
    LOGIN_FORM = '[data-testid="login-form"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.path = "/login"

    def navigate_to_login(self) -> None:
        """Navigate to the login page."""
        self.navigate(self.path)

    def login(self, username: str, password: str) -> None:
        """Perform a standard login with username and password."""
        self.fill(self.USERNAME_INPUT, username)
        self.fill(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)

    def login_with_remember_me(self, username: str, password: str) -> None:
        """Login with the 'Remember Me' option checked."""
        self.fill(self.USERNAME_INPUT, username)
        self.fill(self.PASSWORD_INPUT, password)
        self.check(self.REMEMBER_ME_CHECKBOX)
        self.click(self.LOGIN_BUTTON)

    def click_forgot_password(self) -> None:
        """Click the 'Forgot Password' link."""
        self.click(self.FORGOT_PASSWORD_LINK)

    def click_register(self) -> None:
        """Click the register / sign-up link."""
        self.click(self.REGISTER_LINK)

    def click_social_login_google(self) -> None:
        """Click the Google social login button."""
        self.click(self.SOCIAL_LOGIN_GOOGLE)

    def click_social_login_github(self) -> None:
        """Click the GitHub social login button."""
        self.click(self.SOCIAL_LOGIN_GITHUB)

    def get_error_message(self) -> str:
        """Return the text of the error message element."""
        return self.get_text(self.ERROR_MESSAGE)

    def get_success_message(self) -> str:
        """Return the text of the success message element."""
        return self.get_text(self.SUCCESS_MESSAGE)

    def is_login_form_visible(self) -> bool:
        """Check whether the login form is visible."""
        return self.is_visible(self.LOGIN_FORM)

    def is_error_visible(self) -> bool:
        """Check whether the error message is visible."""
        return self.is_visible(self.ERROR_MESSAGE)

    def clear_fields(self) -> None:
        """Clear both username and password input fields."""
        self.fill(self.USERNAME_INPUT, "")
        self.fill(self.PASSWORD_INPUT, "")
