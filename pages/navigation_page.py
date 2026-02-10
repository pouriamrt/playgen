from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class NavigationPage(BasePage):
    """Page Object for navigation components (navbar, breadcrumbs, footer)."""

    # Selectors
    TOP_NAV = '[data-testid="top-nav"]'
    NAV_LINK_TEMPLATE = '[data-testid="nav-link-{name}"]'
    DROPDOWN_TEMPLATE = '[data-testid="nav-dropdown-{name}"]'
    DROPDOWN_MENU_TEMPLATE = '[data-testid="dropdown-menu-{name}"]'
    HAMBURGER_MENU = '[data-testid="hamburger-menu"]'
    MOBILE_MENU = '[data-testid="mobile-menu"]'
    BREADCRUMBS = '[data-testid="breadcrumbs"]'
    BREADCRUMB_ITEMS = '[data-testid="breadcrumb-item"]'
    FOOTER_NAV = '[data-testid="footer-nav"]'
    SEARCH_BAR = '[data-testid="search-bar"]'
    SEARCH_INPUT = '[data-testid="search-input"]'
    SEARCH_SUBMIT = '[data-testid="search-submit"]'
    LOGO = '[data-testid="logo"]'
    ACTIVE_NAV_LINK = '[data-testid^="nav-link-"].active, [aria-current="page"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def click_nav_link(self, name: str) -> None:
        """Click a navigation link by name."""
        selector = self.NAV_LINK_TEMPLATE.format(name=name)
        self.click(selector)

    def open_dropdown(self, name: str) -> None:
        """Open a dropdown menu in the navigation."""
        trigger = self.DROPDOWN_TEMPLATE.format(name=name)
        self.click(trigger)
        menu = self.DROPDOWN_MENU_TEMPLATE.format(name=name)
        self.wait_for_selector(menu)

    def is_dropdown_open(self, name: str) -> bool:
        """Check if a dropdown menu is currently open."""
        menu = self.DROPDOWN_MENU_TEMPLATE.format(name=name)
        return self.is_visible(menu)

    def toggle_mobile_menu(self) -> None:
        """Toggle the hamburger / mobile menu."""
        self.click(self.HAMBURGER_MENU)

    def is_mobile_menu_open(self) -> bool:
        """Check if the mobile menu is visible."""
        return self.is_visible(self.MOBILE_MENU)

    def get_breadcrumb_trail(self) -> list[str]:
        """Return a list of breadcrumb text items."""
        items = self.page.locator(self.BREADCRUMB_ITEMS)
        return [items.nth(i).inner_text() for i in range(items.count())]

    def search(self, query: str) -> None:
        """Enter a search query and submit."""
        self.fill(self.SEARCH_INPUT, query)
        self.click(self.SEARCH_SUBMIT)

    def get_current_nav_active(self) -> str | None:
        """Return the text of the currently active nav link."""
        if self.is_visible(self.ACTIVE_NAV_LINK):
            return self.get_text(self.ACTIVE_NAV_LINK)
        return None

    def click_logo(self) -> None:
        """Click the site logo."""
        self.click(self.LOGO)

    def is_footer_visible(self) -> bool:
        """Check if the footer navigation is visible."""
        return self.is_visible(self.FOOTER_NAV)
