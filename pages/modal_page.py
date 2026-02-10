from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class ModalPage(BasePage):
    """Page Object for modal / dialog components."""

    # Selectors
    MODAL_OVERLAY = '[data-testid="modal-overlay"]'
    MODAL_CONTENT = '[data-testid="modal-content"]'
    MODAL_TITLE = '[data-testid="modal-title"]'
    MODAL_BODY = '[data-testid="modal-body"]'
    CLOSE_BUTTON = '[data-testid="modal-close"]'
    CONFIRM_BUTTON = '[data-testid="modal-confirm"]'
    CANCEL_BUTTON = '[data-testid="modal-cancel"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def is_open(self) -> bool:
        """Check if the modal is currently open."""
        return self.is_visible(self.MODAL_CONTENT)

    def wait_for_open(self, timeout: float | None = None) -> None:
        """Wait until the modal becomes visible."""
        self.wait_for_selector(self.MODAL_CONTENT, state="visible", timeout=timeout)

    def wait_for_close(self, timeout: float | None = None) -> None:
        """Wait until the modal is no longer visible."""
        self.wait_for_hidden(self.MODAL_CONTENT, timeout=timeout)

    def close(self) -> None:
        """Close the modal using the close (X) button."""
        self.click(self.CLOSE_BUTTON)

    def confirm(self) -> None:
        """Click the confirm / OK button."""
        self.click(self.CONFIRM_BUTTON)

    def cancel(self) -> None:
        """Click the cancel button."""
        self.click(self.CANCEL_BUTTON)

    def get_title(self) -> str:
        """Return the modal title text."""
        return self.get_text(self.MODAL_TITLE)

    def get_body_text(self) -> str:
        """Return the modal body text."""
        return self.get_text(self.MODAL_BODY)

    def close_by_overlay_click(self) -> None:
        """Close the modal by clicking the overlay backdrop."""
        self.click(self.MODAL_OVERLAY)
