from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class FormPage(BasePage):
    """Page Object for generic form interaction patterns."""

    # Selectors
    FORM = '[data-testid="form"]'
    SUBMIT_BUTTON = '[data-testid="form-submit"]'
    CANCEL_BUTTON = '[data-testid="form-cancel"]'
    FIELD_TEMPLATE = '[data-testid="field-{name}"]'
    INPUT_TEMPLATE = '[data-testid="input-{name}"]'
    TEXTAREA_TEMPLATE = '[data-testid="textarea-{name}"]'
    SELECT_TEMPLATE = '[data-testid="select-{name}"]'
    CHECKBOX_TEMPLATE = '[data-testid="checkbox-{name}"]'
    RADIO_TEMPLATE = '[data-testid="radio-{name}-{value}"]'
    DATE_PICKER_TEMPLATE = '[data-testid="datepicker-{name}"]'
    FILE_UPLOAD_TEMPLATE = '[data-testid="file-upload-{name}"]'
    VALIDATION_ERROR_TEMPLATE = '[data-testid="error-{field}"]'
    REQUIRED_INDICATOR_TEMPLATE = '[data-testid="required-{field}"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def fill_field(self, name: str, value: str) -> None:
        """Fill a text input field by name."""
        selector = self.INPUT_TEMPLATE.format(name=name)
        self.fill(selector, value)

    def fill_textarea(self, name: str, value: str) -> None:
        """Fill a textarea field by name."""
        selector = self.TEXTAREA_TEMPLATE.format(name=name)
        self.fill(selector, value)

    def select_dropdown(self, name: str, value: str) -> None:
        """Select an option from a dropdown by name and value."""
        selector = self.SELECT_TEMPLATE.format(name=name)
        self.select_option(selector, value=value)

    def check_checkbox(self, name: str) -> None:
        """Check a checkbox by name."""
        selector = self.CHECKBOX_TEMPLATE.format(name=name)
        self.check(selector)

    def uncheck_checkbox(self, name: str) -> None:
        """Uncheck a checkbox by name."""
        selector = self.CHECKBOX_TEMPLATE.format(name=name)
        self.uncheck(selector)

    def select_radio(self, name: str, value: str) -> None:
        """Select a radio button by name and value."""
        selector = self.RADIO_TEMPLATE.format(name=name, value=value)
        self.check(selector)

    def set_date(self, name: str, date_value: str) -> None:
        """Fill a date-picker input."""
        selector = self.DATE_PICKER_TEMPLATE.format(name=name)
        self.fill(selector, date_value)

    def upload_file(self, name: str, file_path: str) -> None:
        """Upload a file to a file-upload input."""
        selector = self.FILE_UPLOAD_TEMPLATE.format(name=name)
        self.page.set_input_files(selector, file_path)

    def submit(self) -> None:
        """Click the form submit button."""
        self.click(self.SUBMIT_BUTTON)

    def cancel(self) -> None:
        """Click the form cancel button."""
        self.click(self.CANCEL_BUTTON)

    def get_validation_error(self, field: str) -> str:
        """Return the validation error text for a field."""
        selector = self.VALIDATION_ERROR_TEMPLATE.format(field=field)
        return self.get_text(selector)

    def is_validation_error_visible(self, field: str) -> bool:
        """Check if a validation error is visible for a field."""
        selector = self.VALIDATION_ERROR_TEMPLATE.format(field=field)
        return self.is_visible(selector)

    def is_field_required(self, field: str) -> bool:
        """Check if a field shows a required indicator."""
        selector = self.REQUIRED_INDICATOR_TEMPLATE.format(field=field)
        return self.is_visible(selector)

    def get_field_value(self, name: str) -> str:
        """Return the current value of an input field."""
        selector = self.INPUT_TEMPLATE.format(name=name)
        return self.get_input_value(selector)

    def clear_form(self) -> None:
        """Clear all visible input and textarea fields in the form."""
        form = self.page.locator(self.FORM)
        inputs = form.locator("input[type='text'], input[type='email'], input[type='password'], textarea")
        for i in range(inputs.count()):
            inputs.nth(i).fill("")
