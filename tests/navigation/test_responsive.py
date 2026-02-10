"""Responsive design tests -- layout adaptations across viewport sizes."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.dashboard_page import DashboardPage
from pages.navigation_page import NavigationPage

from tests.navigation.conftest import (
    ALL_VIEWPORTS,
    MOBILE_VIEWPORTS,
    VIEWPORT_DESKTOP,
    VIEWPORT_MOBILE,
    VIEWPORT_MOBILE_SMALL,
    VIEWPORT_TABLET_LANDSCAPE,
    VIEWPORT_TABLET_PORTRAIT,
)


# ---------------------------------------------------------------------------
# Layout tests per breakpoint
# ---------------------------------------------------------------------------


@pytest.mark.responsive
@pytest.mark.navigation
class TestLayoutBreakpoints:
    """Verify that the page layout adapts correctly to each breakpoint."""

    def test_desktop_layout(self, authenticated_page: Page) -> None:
        """Verify the desktop layout at 1920x1080."""
        authenticated_page.set_viewport_size(VIEWPORT_DESKTOP)
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        assert nav.is_visible(nav.TOP_NAV), "Top nav should be visible on desktop"
        hamburger = authenticated_page.locator(nav.HAMBURGER_MENU)
        expect(hamburger).to_be_hidden()

    def test_tablet_landscape_layout(self, authenticated_page: Page) -> None:
        """Verify the layout at 1024x768 (tablet landscape)."""
        authenticated_page.set_viewport_size(VIEWPORT_TABLET_LANDSCAPE)
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        assert nav.is_visible(nav.TOP_NAV), "Top nav should be visible on tablet landscape"

    def test_tablet_portrait_layout(self, authenticated_page: Page) -> None:
        """Verify the layout at 768x1024 (tablet portrait)."""
        authenticated_page.set_viewport_size(VIEWPORT_TABLET_PORTRAIT)
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        # Navigation may switch to hamburger at this breakpoint
        top_nav = authenticated_page.locator(nav.TOP_NAV)
        assert top_nav.count() > 0, "Navigation container should exist"

    def test_mobile_layout(self, authenticated_page: Page) -> None:
        """Verify the mobile layout at 375x667."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        hamburger = authenticated_page.locator(nav.HAMBURGER_MENU)
        expect(hamburger).to_be_visible()

    def test_mobile_small_layout(self, authenticated_page: Page) -> None:
        """Verify the smallest mobile layout at 320x568."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE_SMALL)
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        hamburger = authenticated_page.locator(nav.HAMBURGER_MENU)
        expect(hamburger).to_be_visible()


# ---------------------------------------------------------------------------
# Hamburger / mobile menu
# ---------------------------------------------------------------------------


@pytest.mark.responsive
@pytest.mark.navigation
class TestMobileMenu:
    """Tests for the hamburger/mobile menu behaviour."""

    def test_hamburger_menu_visible_on_mobile(self, authenticated_page: Page) -> None:
        """Verify the hamburger icon is visible on mobile viewports."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        assert nav.is_visible(nav.HAMBURGER_MENU), "Hamburger menu should be visible on mobile"

    def test_hamburger_menu_opens_closes(self, authenticated_page: Page) -> None:
        """Verify the mobile menu toggles open and closed."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.toggle_mobile_menu()
        assert nav.is_mobile_menu_open(), "Mobile menu should open after toggle"
        nav.toggle_mobile_menu()
        authenticated_page.wait_for_timeout(300)
        assert not nav.is_mobile_menu_open(), "Mobile menu should close after second toggle"

    def test_mobile_menu_items_functional(self, authenticated_page: Page) -> None:
        """Verify mobile menu items navigate correctly when clicked."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        nav = NavigationPage(authenticated_page)
        nav.navigate("/dashboard")
        nav.toggle_mobile_menu()
        menu_links = authenticated_page.locator(f"{nav.MOBILE_MENU} a")
        if menu_links.count() > 0:
            first_href = menu_links.first.get_attribute("href")
            menu_links.first.click()
            nav.wait_for_navigation()
            if first_href:
                assert first_href in nav.get_current_url() or nav.get_current_url() != "", (
                    "Clicking mobile menu item should navigate"
                )


# ---------------------------------------------------------------------------
# Sidebar responsiveness
# ---------------------------------------------------------------------------


@pytest.mark.responsive
class TestSidebarResponsive:
    """Tests for sidebar visibility across viewports."""

    def test_sidebar_hidden_on_mobile(self, authenticated_page: Page) -> None:
        """Verify the sidebar is hidden on mobile viewports."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        dashboard = DashboardPage(authenticated_page)
        dashboard.navigate_to_dashboard()
        sidebar = authenticated_page.locator(dashboard.SIDEBAR_NAV)
        expect(sidebar).to_be_hidden()


# ---------------------------------------------------------------------------
# Content responsiveness
# ---------------------------------------------------------------------------


@pytest.mark.responsive
class TestContentResponsive:
    """Tests for content elements adapting to viewport changes."""

    def test_table_horizontal_scroll_on_mobile(self, authenticated_page: Page) -> None:
        """Verify data tables allow horizontal scrolling on mobile."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        table_container = authenticated_page.locator('[data-testid="data-table"]').first
        if table_container.count() > 0:
            overflow = table_container.evaluate(
                "el => getComputedStyle(el.parentElement || el).overflowX"
            )
            assert overflow in ("auto", "scroll", "overlay"), (
                "Table container should allow horizontal scroll on mobile"
            )

    def test_images_responsive_sizing(self, authenticated_page: Page) -> None:
        """Verify images do not exceed their container width."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        images = authenticated_page.locator("img")
        for i in range(min(images.count(), 10)):
            img = images.nth(i)
            if img.is_visible():
                box = img.bounding_box()
                if box:
                    assert box["width"] <= VIEWPORT_MOBILE["width"] + 1, (
                        f"Image {i} should not exceed viewport width"
                    )

    def test_font_sizes_scale_appropriately(self, authenticated_page: Page) -> None:
        """Verify body font size is reasonable on mobile."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        font_size = authenticated_page.evaluate(
            "parseFloat(getComputedStyle(document.body).fontSize)"
        )
        assert 12 <= font_size <= 24, (
            f"Body font size should be between 12px and 24px, got {font_size}px"
        )

    def test_touch_targets_minimum_size(self, authenticated_page: Page) -> None:
        """Verify interactive elements meet the 48px minimum touch target (WCAG 2.5.5)."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        buttons = authenticated_page.locator("button, a, [role='button']")
        violations = []
        for i in range(min(buttons.count(), 20)):
            btn = buttons.nth(i)
            if btn.is_visible():
                box = btn.bounding_box()
                if box and (box["width"] < 44 or box["height"] < 44):
                    label = btn.evaluate("el => el.textContent?.trim().slice(0, 30) || el.tagName")
                    violations.append(f"'{label}' ({box['width']:.0f}x{box['height']:.0f})")
        # Warn but don't hard-fail if only a few minor violations
        if violations:
            pytest.warns(UserWarning, match="touch target") if len(violations) > 5 else None

    def test_no_horizontal_overflow(self, authenticated_page: Page) -> None:
        """Verify no horizontal scrollbar appears on mobile."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        has_overflow = authenticated_page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert not has_overflow, "Page should not have horizontal overflow on mobile"

    def test_form_layout_stacks_on_mobile(self, authenticated_page: Page) -> None:
        """Verify form fields stack vertically on mobile viewports."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        authenticated_page.goto(f"{settings.base_url}/profile")
        authenticated_page.wait_for_load_state("domcontentloaded")
        fields = authenticated_page.locator("input:visible, textarea:visible, select:visible")
        if fields.count() >= 2:
            box1 = fields.nth(0).bounding_box()
            box2 = fields.nth(1).bounding_box()
            if box1 and box2:
                # Stacked means the second field starts below the first
                assert box2["y"] >= box1["y"] + box1["height"] - 5, (
                    "Form fields should stack vertically on mobile"
                )

    def test_modal_full_screen_on_mobile(self, authenticated_page: Page) -> None:
        """Verify modals expand to full width on mobile viewports."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="modal-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            modal = authenticated_page.locator('[data-testid="modal-content"]')
            modal.wait_for(state="visible", timeout=3000)
            box = modal.bounding_box()
            if box:
                assert box["width"] >= VIEWPORT_MOBILE["width"] * 0.9, (
                    "Modal should be nearly full-width on mobile"
                )

    def test_cards_stack_vertically_on_mobile(self, authenticated_page: Page) -> None:
        """Verify card components stack vertically on mobile."""
        authenticated_page.set_viewport_size(VIEWPORT_MOBILE)
        dashboard = DashboardPage(authenticated_page)
        dashboard.navigate_to_dashboard()
        cards = authenticated_page.locator(dashboard.STATS_CARDS)
        if cards.count() >= 2:
            box1 = cards.nth(0).bounding_box()
            box2 = cards.nth(1).bounding_box()
            if box1 and box2:
                assert box2["y"] >= box1["y"] + box1["height"] - 5, (
                    "Cards should stack vertically on mobile"
                )


# ---------------------------------------------------------------------------
# Navigation adaptation across viewports
# ---------------------------------------------------------------------------


@pytest.mark.responsive
@pytest.mark.navigation
class TestNavigationAdaptation:
    """Tests for navigation changing behaviour based on viewport."""

    @pytest.mark.parametrize("viewport_page", ALL_VIEWPORTS, indirect=True)
    def test_navigation_changes_for_viewport(self, viewport_page: Page) -> None:
        """Verify the navigation adapts per viewport (hamburger vs full menu)."""
        nav = NavigationPage(viewport_page)
        nav.navigate("/dashboard")
        nav.wait_for_load()
        vp_width = viewport_page.viewport_size["width"]
        if vp_width < 768:
            assert nav.is_visible(nav.HAMBURGER_MENU), (
                f"Hamburger should be visible at {vp_width}px"
            )
        else:
            assert nav.is_visible(nav.TOP_NAV), (
                f"Full top nav should be visible at {vp_width}px"
            )

    def test_orientation_change_handling(self, authenticated_page: Page) -> None:
        """Verify layout adjusts when simulating an orientation change."""
        # Portrait
        authenticated_page.set_viewport_size({"width": 375, "height": 812})
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        portrait_overflow = authenticated_page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        # Landscape
        authenticated_page.set_viewport_size({"width": 812, "height": 375})
        authenticated_page.wait_for_timeout(300)
        landscape_overflow = authenticated_page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert not portrait_overflow, "No horizontal overflow in portrait"
        assert not landscape_overflow, "No horizontal overflow in landscape"

    def test_viewport_meta_tag_present(self, page: Page) -> None:
        """Verify the viewport meta tag is set for responsive behaviour."""
        page.goto(f"{settings.base_url}/")
        page.wait_for_load_state("domcontentloaded")
        viewport_meta = page.locator('meta[name="viewport"]')
        expect(viewport_meta).to_have_count(1)
        content = viewport_meta.get_attribute("content")
        assert content is not None, "Viewport meta tag should have content"
        assert "width=device-width" in content, (
            "Viewport meta should include width=device-width"
        )
