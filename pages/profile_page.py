from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from pages.base_page import BasePage


class ProfilePage(BasePage):
    """Page Object for the User Profile page."""

    # Selectors
    AVATAR = '[data-testid="profile-avatar"]'
    AVATAR_UPLOAD = '[data-testid="avatar-upload"]'
    FIRST_NAME_INPUT = '[data-testid="profile-first-name"]'
    LAST_NAME_INPUT = '[data-testid="profile-last-name"]'
    EMAIL_INPUT = '[data-testid="profile-email"]'
    PHONE_INPUT = '[data-testid="profile-phone"]'
    BIO_INPUT = '[data-testid="profile-bio"]'
    SAVE_BUTTON = '[data-testid="profile-save-button"]'
    SUCCESS_MESSAGE = '[data-testid="profile-success-message"]'

    # Change password section
    CURRENT_PASSWORD_INPUT = '[data-testid="current-password"]'
    NEW_PASSWORD_INPUT = '[data-testid="new-password"]'
    CONFIRM_NEW_PASSWORD_INPUT = '[data-testid="confirm-new-password"]'
    CHANGE_PASSWORD_BUTTON = '[data-testid="change-password-button"]'

    # Notification preferences
    NOTIFICATION_TOGGLE_TEMPLATE = '[data-testid="notification-toggle-{type}"]'

    # Account management
    DELETE_ACCOUNT_BUTTON = '[data-testid="delete-account-button"]'
    CONFIRM_DELETE_BUTTON = '[data-testid="confirm-delete-button"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.path = "/profile"

    def navigate_to_profile(self) -> None:
        """Navigate to the profile page."""
        self.navigate(self.path)

    def update_profile(self, data: dict[str, str]) -> None:
        """Update profile fields from a dict and save."""
        field_map = {
            "first_name": self.FIRST_NAME_INPUT,
            "last_name": self.LAST_NAME_INPUT,
            "email": self.EMAIL_INPUT,
            "phone": self.PHONE_INPUT,
            "bio": self.BIO_INPUT,
        }
        for key, selector in field_map.items():
            if key in data:
                self.fill(selector, data[key])
        self.click(self.SAVE_BUTTON)

    def get_profile_data(self) -> dict[str, str]:
        """Return the current values of all profile fields."""
        return {
            "first_name": self.get_input_value(self.FIRST_NAME_INPUT),
            "last_name": self.get_input_value(self.LAST_NAME_INPUT),
            "email": self.get_input_value(self.EMAIL_INPUT),
            "phone": self.get_input_value(self.PHONE_INPUT),
            "bio": self.get_input_value(self.BIO_INPUT),
        }

    def change_password(self, old_password: str, new_password: str, confirm_password: str) -> None:
        """Fill and submit the change-password form."""
        self.fill(self.CURRENT_PASSWORD_INPUT, old_password)
        self.fill(self.NEW_PASSWORD_INPUT, new_password)
        self.fill(self.CONFIRM_NEW_PASSWORD_INPUT, confirm_password)
        self.click(self.CHANGE_PASSWORD_BUTTON)

    def upload_avatar(self, file_path: str) -> None:
        """Upload a new avatar image."""
        self.page.set_input_files(self.AVATAR_UPLOAD, file_path)

    def toggle_notification(self, notification_type: str) -> None:
        """Toggle a notification preference on or off."""
        selector = self.NOTIFICATION_TOGGLE_TEMPLATE.format(type=notification_type)
        self.click(selector)

    def delete_account(self) -> None:
        """Click delete account and confirm the deletion."""
        self.click(self.DELETE_ACCOUNT_BUTTON)
        self.wait_for_selector(self.CONFIRM_DELETE_BUTTON)
        self.click(self.CONFIRM_DELETE_BUTTON)

    def is_success_message_visible(self) -> bool:
        """Check if the profile update success message is visible."""
        return self.is_visible(self.SUCCESS_MESSAGE)

    def get_success_message(self) -> str:
        """Return the text of the success message."""
        return self.get_text(self.SUCCESS_MESSAGE)
