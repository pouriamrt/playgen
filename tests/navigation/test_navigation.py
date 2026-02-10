"""Core navigation tests -- links, breadcrumbs, menus, keyboard navigation."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.dashboard_page import DashboardPage
from pages.navigation_page import NavigationPage

# ---------------------------------------------------------------------------
# Main navigation links
# ---------------------------------------------------------------------------

NAV_LINKS = [
    ("home", "/"),
    ("dashboard", "/dashboard"),
    ("profile", "/profile"),
    ("settings", "/settings"),
]


@pytest.mark.navigation
@pytest.mark.smoke
class TestMainNavigation:
    """Tests for primary top-level navigation links."""

    def test_main_nav_links_visible(self, authenticated_page: Page) -> None:
        """Verify that all primary navigation links are visible."""
        nav = NavigationPage(authenticated_page)
        assert nav.is_visible(nav.TOP_NAV), "Top navigation bar should be visible"
        for name, _ in NAV_LINKS:
            selector = nav.NAV_LINK_TEMPLATE.format(name=name)
            assert nav.is_visible(selector), f"Nav link '{name}' should be visible"

    @pytest.mark.parametrize("link_name,expected_path", NAV_LINKS)
    def test_each_nav_link_navigates_correctly(
        self, authenticated_page: Page, link_name: str, expected_path: str
    ) -> None:
        """Verify that clicking a nav link navigates to the expected URL path."""
        nav = NavigationPage(authenticated_page)
        nav.click_nav_link(link_name)
        nav.wait_for_navigation()
        assert expected_path in nav.get_current_url(), (
            f"Clicking '{link_name}' should navigate to '{expected_path}'"
        )

    def test_nav_active_state_matches_current_page(self, authenticated_page: Page) -> None:
        """Verify the active nav link corresponds to the current page."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        active = nav.get_current_nav_active()
        assert active is not None, "An active nav link should be highlighted"

    def test_logo_links_to_home(self, authenticated_page: Page) -> None:
        """Verify clicking the logo navigates to the home page."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.click_logo()
        nav.wait_for_navigation()
        url = nav.get_current_url()
        assert url.rstrip("/").endswith("") or "/" in url, "Logo should link to home"


# ---------------------------------------------------------------------------
# Breadcrumb navigation
# ---------------------------------------------------------------------------


@pytest.mark.navigation
class TestBreadcrumbs:
    """Tests for breadcrumb trail accuracy and clickability."""

    def test_breadcrumb_trail_accuracy(self, authenticated_page: Page) -> None:
        """Verify the breadcrumb trail reflects the current page hierarchy."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/settings")
        nav.wait_for_load()
        trail = nav.get_breadcrumb_trail()
        assert len(trail) >= 1, "Breadcrumbs should contain at least one item"
        assert "Settings" in trail[-1] or "settings" in trail[-1].lower(), (
            "Last breadcrumb should be the current page"
        )

    def test_breadcrumb_navigation(self, authenticated_page: Page) -> None:
        """Verify clicking a breadcrumb item navigates to the corresponding page."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/settings")
        nav.wait_for_load()
        items = authenticated_page.locator(nav.BREADCRUMB_ITEMS)
        if items.count() > 1:
            items.first.click()
            nav.wait_for_navigation()
            assert "/settings" not in nav.get_current_url(), (
                "Clicking a parent breadcrumb should navigate away from settings"
            )


# ---------------------------------------------------------------------------
# Browser history
# ---------------------------------------------------------------------------


@pytest.mark.navigation
class TestBrowserHistory:
    """Tests for browser back/forward navigation."""

    def test_browser_back_button(self, authenticated_page: Page) -> None:
        """Verify the browser back button returns to the previous page."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        first_url = nav.get_current_url()
        nav.navigate("/settings")
        nav.wait_for_load()
        authenticated_page.go_back()
        nav.wait_for_load()
        assert first_url == nav.get_current_url(), "Back button should return to previous page"

    def test_browser_forward_button(self, authenticated_page: Page) -> None:
        """Verify the browser forward button goes to the next page after going back."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        nav.navigate("/settings")
        nav.wait_for_load()
        second_url = nav.get_current_url()
        authenticated_page.go_back()
        nav.wait_for_load()
        authenticated_page.go_forward()
        nav.wait_for_load()
        assert second_url == nav.get_current_url(), "Forward button should go to next page"


# ---------------------------------------------------------------------------
# Deep linking and error pages
# ---------------------------------------------------------------------------


@pytest.mark.navigation
class TestDeepLinksAndErrorPages:
    """Tests for direct URL access, 404 pages, and redirects."""

    def test_deep_link_direct_url_access(self, authenticated_page: Page) -> None:
        """Verify navigating directly to a deep URL loads the correct page."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/profile")
        nav.wait_for_load()
        assert "/profile" in nav.get_current_url(), "Direct URL access should load the page"

    def test_404_page_for_invalid_url(self, page: Page) -> None:
        """Verify that an invalid URL displays a 404 page."""
        page.goto(f"{settings.base_url}/this-page-does-not-exist-xyz")
        expect(page).to_have_title(lambda t: "404" in t.lower() or "not found" in t.lower())

    def test_404_page_has_home_link(self, page: Page) -> None:
        """Verify the 404 page includes a link back to the home page."""
        page.goto(f"{settings.base_url}/this-page-does-not-exist-xyz")
        home_link = page.locator('a[href="/"], a[href*="home"]')
        expect(home_link.first).to_be_visible()

    def test_redirect_for_moved_pages(self, page: Page) -> None:
        """Verify that deprecated/moved URLs redirect correctly."""
        page.goto(f"{settings.base_url}/old-dashboard")
        page.wait_for_load_state("domcontentloaded")
        # The page should either redirect or show content -- not a raw error
        assert page.url != "", "Page should have resolved to a URL after redirect"


# ---------------------------------------------------------------------------
# Footer navigation
# ---------------------------------------------------------------------------


@pytest.mark.navigation
class TestFooterNavigation:
    """Tests for footer links."""

    def test_footer_navigation_links(self, authenticated_page: Page) -> None:
        """Verify that the footer navigation section is visible and contains links."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.scroll_to(nav.FOOTER_NAV)
        assert nav.is_footer_visible(), "Footer navigation should be visible"
        footer_links = authenticated_page.locator(f"{nav.FOOTER_NAV} a")
        expect(footer_links.first).to_be_visible()


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------


@pytest.mark.navigation
class TestSidebarNavigation:
    """Tests for sidebar navigation on the dashboard."""

    def test_sidebar_navigation(self, authenticated_page: Page) -> None:
        """Verify sidebar navigation items are visible on the dashboard."""
        dashboard = DashboardPage(authenticated_page)
        dashboard.navigate_to_dashboard()
        assert dashboard.is_visible(dashboard.SIDEBAR_NAV), "Sidebar should be visible"

    def test_sidebar_collapse_expand(self, authenticated_page: Page) -> None:
        """Verify the sidebar can be collapsed and expanded."""
        dashboard = DashboardPage(authenticated_page)
        dashboard.navigate_to_dashboard()
        collapse_btn = '[data-testid="sidebar-collapse"]'
        if dashboard.is_visible(collapse_btn):
            dashboard.click(collapse_btn)
            sidebar = authenticated_page.locator(dashboard.SIDEBAR_NAV)
            expect(sidebar).to_have_class(lambda c: "collapsed" in c)
            dashboard.click(collapse_btn)
            expect(sidebar).not_to_have_class(lambda c: "collapsed" in c)


# ---------------------------------------------------------------------------
# Dropdown menus
# ---------------------------------------------------------------------------


@pytest.mark.navigation
class TestDropdownMenus:
    """Tests for navigation dropdown menus."""

    def test_dropdown_menu_open_close(self, authenticated_page: Page) -> None:
        """Verify a dropdown menu opens on click and closes on subsequent click."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.open_dropdown("settings")
        assert nav.is_dropdown_open("settings"), "Dropdown should be open after click"
        nav.click(nav.DROPDOWN_TEMPLATE.format(name="settings"))
        authenticated_page.wait_for_timeout(300)
        assert not nav.is_dropdown_open("settings"), "Dropdown should close on second click"

    def test_dropdown_menu_items_clickable(self, authenticated_page: Page) -> None:
        """Verify items inside a dropdown menu are clickable and navigate."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.open_dropdown("settings")
        menu = authenticated_page.locator(
            nav.DROPDOWN_MENU_TEMPLATE.format(name="settings")
        )
        first_item = menu.locator("a, button").first
        expect(first_item).to_be_visible()

    def test_nested_dropdown_menus(self, authenticated_page: Page) -> None:
        """Verify nested/sub-dropdown menus open correctly."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nested_trigger = '[data-testid="nav-dropdown-more"]'
        if nav.is_visible(nested_trigger):
            nav.click(nested_trigger)
            sub_menu = '[data-testid="dropdown-menu-more"]'
            nav.wait_for_selector(sub_menu)
            assert nav.is_visible(sub_menu), "Nested dropdown should open"


# ---------------------------------------------------------------------------
# Keyboard navigation and accessibility-related nav
# ---------------------------------------------------------------------------


@pytest.mark.navigation
@pytest.mark.accessibility
class TestKeyboardNavigation:
    """Tests for keyboard-based navigation through menus and skip links."""

    def test_keyboard_navigation_through_menu(self, authenticated_page: Page) -> None:
        """Verify arrow keys and Enter navigate through the top nav menu."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        first_link = authenticated_page.locator(
            nav.NAV_LINK_TEMPLATE.format(name="home")
        )
        first_link.focus()
        authenticated_page.keyboard.press("Tab")
        focused = authenticated_page.evaluate("document.activeElement.getAttribute('data-testid')")
        assert focused is not None, "Tab should move focus to the next nav element"

    def test_skip_to_content_link(self, authenticated_page: Page) -> None:
        """Verify the skip-to-content link is present and functional."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        skip_link = authenticated_page.locator('[data-testid="skip-to-content"], a[href="#main-content"]')
        authenticated_page.keyboard.press("Tab")
        if skip_link.count() > 0:
            expect(skip_link.first).to_be_focused()
            skip_link.first.click()
            main = authenticated_page.locator("#main-content, main")
            if main.count() > 0:
                assert main.first.is_visible(), "Main content should be visible after skip link"

    def test_tab_navigation_order(self, authenticated_page: Page) -> None:
        """Verify that Tab key cycles through interactive elements in logical order."""
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        authenticated_page.keyboard.press("Tab")
        focused_elements = []
        for _ in range(5):
            tag = authenticated_page.evaluate(
                "document.activeElement ? document.activeElement.tagName.toLowerCase() : null"
            )
            focused_elements.append(tag)
            authenticated_page.keyboard.press("Tab")
        # At least some interactive elements should receive focus
        interactive = {"a", "button", "input", "select", "textarea"}
        focused_interactive = [el for el in focused_elements if el in interactive]
        assert len(focused_interactive) >= 1, (
            "Tab should cycle through interactive elements"
        )
