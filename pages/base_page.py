from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import FrameLocator, Locator, Page

from config.settings import settings


class BasePage:
    """Base Page Object with common methods shared by all page objects.

    All page objects should inherit from this class and use Playwright's sync API.
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.page.set_default_timeout(settings.default_timeout)

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def navigate(self, path: str = "/") -> None:
        """Navigate to a path relative to the base URL."""
        url = f"{settings.base_url.rstrip('/')}/{path.lstrip('/')}"
        self.page.goto(url, wait_until="domcontentloaded")

    def wait_for_load(self) -> None:
        """Wait for the page to finish loading."""
        self.page.wait_for_load_state("networkidle")

    def get_title(self) -> str:
        """Return the page title."""
        return self.page.title()

    def get_current_url(self) -> str:
        """Return the current page URL."""
        return self.page.url

    # -------------------------------------------------------------------------
    # Element interaction
    # -------------------------------------------------------------------------

    def click(self, selector: str) -> None:
        """Click an element identified by selector."""
        self.page.click(selector)

    def fill(self, selector: str, value: str) -> None:
        """Clear and fill an input element with the given value."""
        self.page.fill(selector, value)

    def select_option(self, selector: str, value: str | None = None, label: str | None = None) -> list[str]:
        """Select an option from a <select> element by value or label."""
        kwargs: dict[str, str] = {}
        if value is not None:
            kwargs["value"] = value
        if label is not None:
            kwargs["label"] = label
        return self.page.select_option(selector, **kwargs)

    def check(self, selector: str) -> None:
        """Check a checkbox or radio button."""
        self.page.check(selector)

    def uncheck(self, selector: str) -> None:
        """Uncheck a checkbox."""
        self.page.uncheck(selector)

    def type_text(self, selector: str, text: str, delay: float = 0) -> None:
        """Type text character by character into an element."""
        self.page.type(selector, text, delay=delay)

    # -------------------------------------------------------------------------
    # Element state queries
    # -------------------------------------------------------------------------

    def is_visible(self, selector: str, timeout: float | None = None) -> bool:
        """Check if an element is visible on the page."""
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout or 3000)
            return True
        except Exception:
            return False

    def is_enabled(self, selector: str) -> bool:
        """Check if an element is enabled."""
        return self.page.is_enabled(selector)

    def is_checked(self, selector: str) -> bool:
        """Check if a checkbox/radio is checked."""
        return self.page.is_checked(selector)

    def get_text(self, selector: str) -> str:
        """Get the inner text of an element."""
        return self.page.inner_text(selector)

    def get_input_value(self, selector: str) -> str:
        """Get the value of an input element."""
        return self.page.input_value(selector)

    def get_attribute(self, selector: str, attribute: str) -> str | None:
        """Get an attribute value from an element."""
        return self.page.get_attribute(selector, attribute)

    def get_element_count(self, selector: str) -> int:
        """Count elements matching the selector."""
        return self.page.locator(selector).count()

    # -------------------------------------------------------------------------
    # Waiting
    # -------------------------------------------------------------------------

    def wait_for_selector(self, selector: str, state: str = "visible", timeout: float | None = None) -> Locator:
        """Wait for a selector to reach the specified state."""
        self.page.wait_for_selector(selector, state=state, timeout=timeout)
        return self.page.locator(selector)

    def wait_for_navigation(self, url: str | None = None, timeout: float | None = None) -> None:
        """Wait for navigation to complete, optionally to a specific URL pattern."""
        if url:
            self.page.wait_for_url(url, timeout=timeout)
        else:
            self.page.wait_for_load_state("domcontentloaded")

    def wait_for_hidden(self, selector: str, timeout: float | None = None) -> None:
        """Wait for an element to become hidden."""
        self.page.wait_for_selector(selector, state="hidden", timeout=timeout)

    # -------------------------------------------------------------------------
    # Scrolling and hover
    # -------------------------------------------------------------------------

    def scroll_to(self, selector: str) -> None:
        """Scroll the page so the element is visible."""
        self.page.locator(selector).scroll_into_view_if_needed()

    def hover(self, selector: str) -> None:
        """Hover over an element."""
        self.page.hover(selector)

    # -------------------------------------------------------------------------
    # Screenshots
    # -------------------------------------------------------------------------

    def take_screenshot(self, name: str = "screenshot", full_page: bool = False) -> Path:
        """Take a screenshot and save it to the screenshots directory."""
        settings.ensure_artifact_dirs()
        filepath = settings.screenshots_dir / f"{name}.png"
        self.page.screenshot(path=str(filepath), full_page=full_page)
        return filepath

    # -------------------------------------------------------------------------
    # Alerts / Dialogs
    # -------------------------------------------------------------------------

    def accept_alert(self, handler: Any = None) -> None:
        """Set up a handler to accept the next dialog (alert/confirm/prompt)."""
        self.page.on("dialog", lambda dialog: dialog.accept(handler))

    def dismiss_alert(self) -> None:
        """Set up a handler to dismiss the next dialog."""
        self.page.on("dialog", lambda dialog: dialog.dismiss())

    # -------------------------------------------------------------------------
    # Frames and tabs
    # -------------------------------------------------------------------------

    def switch_to_frame(self, selector: str) -> FrameLocator:
        """Return a FrameLocator for the iframe matching the selector."""
        return self.page.frame_locator(selector)

    def switch_to_new_tab(self) -> Page:
        """Wait for a new page/tab and return it."""
        with self.page.context.expect_page() as new_page_info:
            pass
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        return new_page

    # -------------------------------------------------------------------------
    # Locator helpers
    # -------------------------------------------------------------------------

    def locator(self, selector: str) -> Locator:
        """Return a Playwright Locator for the given selector."""
        return self.page.locator(selector)

    def get_by_test_id(self, test_id: str) -> Locator:
        """Get an element by its data-testid attribute."""
        return self.page.get_by_test_id(test_id)

    def get_by_role(self, role: str, **kwargs: Any) -> Locator:
        """Get an element by its ARIA role."""
        return self.page.get_by_role(role, **kwargs)

    def get_by_text(self, text: str, exact: bool = False) -> Locator:
        """Get an element by its text content."""
        return self.page.get_by_text(text, exact=exact)
