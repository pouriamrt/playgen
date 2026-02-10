from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class SettingsPage(BasePage):
    """Page Object for the application Settings page."""

    # Selectors
    SETTINGS_SECTION_TEMPLATE = '[data-testid="settings-section-{section}"]'
    TOGGLE_TEMPLATE = '[data-testid="toggle-{name}"]'
    SETTING_INPUT_TEMPLATE = '[data-testid="setting-{name}"]'
    SAVE_BUTTON_TEMPLATE = '[data-testid="save-{section}"]'
    SAVE_ALL_BUTTON = '[data-testid="save-all-settings"]'
    THEME_SELECTOR = '[data-testid="theme-selector"]'
    LANGUAGE_SELECTOR = '[data-testid="language-selector"]'
    TIMEZONE_SELECTOR = '[data-testid="timezone-selector"]'
    EMAIL_PREFERENCE_TEMPLATE = '[data-testid="email-pref-{name}"]'
    SUCCESS_MESSAGE = '[data-testid="settings-success"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.path = "/settings"

    def navigate_to_settings(self) -> None:
        """Navigate to the settings page."""
        self.navigate(self.path)

    def toggle_setting(self, name: str) -> None:
        """Toggle a switch setting on or off."""
        selector = self.TOGGLE_TEMPLATE.format(name=name)
        self.click(selector)

    def update_setting(self, name: str, value: str) -> None:
        """Update a text-based setting input."""
        selector = self.SETTING_INPUT_TEMPLATE.format(name=name)
        self.fill(selector, value)

    def get_setting_value(self, name: str) -> str:
        """Return the current value of a text-based setting."""
        selector = self.SETTING_INPUT_TEMPLATE.format(name=name)
        return self.get_input_value(selector)

    def is_toggle_enabled(self, name: str) -> bool:
        """Check if a toggle switch is on."""
        selector = self.TOGGLE_TEMPLATE.format(name=name)
        return self.is_checked(selector)

    def save_section(self, section: str) -> None:
        """Save a specific settings section."""
        selector = self.SAVE_BUTTON_TEMPLATE.format(section=section)
        self.click(selector)

    def save_all(self) -> None:
        """Save all settings at once."""
        self.click(self.SAVE_ALL_BUTTON)

    def select_theme(self, theme: str) -> None:
        """Select a theme (e.g., 'light', 'dark', 'system')."""
        self.select_option(self.THEME_SELECTOR, value=theme)

    def get_selected_theme(self) -> str:
        """Return the currently selected theme value."""
        return self.get_input_value(self.THEME_SELECTOR)

    def select_language(self, lang: str) -> None:
        """Select a language."""
        self.select_option(self.LANGUAGE_SELECTOR, value=lang)

    def get_selected_language(self) -> str:
        """Return the currently selected language value."""
        return self.get_input_value(self.LANGUAGE_SELECTOR)

    def select_timezone(self, timezone: str) -> None:
        """Select a timezone."""
        self.select_option(self.TIMEZONE_SELECTOR, value=timezone)

    def toggle_email_preference(self, name: str) -> None:
        """Toggle an email notification preference."""
        selector = self.EMAIL_PREFERENCE_TEMPLATE.format(name=name)
        self.click(selector)

    def is_success_message_visible(self) -> bool:
        """Check if the settings save success message is displayed."""
        return self.is_visible(self.SUCCESS_MESSAGE)
