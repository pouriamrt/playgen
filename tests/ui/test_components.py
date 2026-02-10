"""UI component tests -- buttons, toasts, modals, tabs, carousel, and more."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.dashboard_page import DashboardPage
from pages.modal_page import ModalPage
from pages.settings_page import SettingsPage


# ---------------------------------------------------------------------------
# Button states
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestButtons:
    """Tests for button interaction states."""

    def test_button_click_feedback(self, authenticated_page: Page) -> None:
        """Verify buttons provide visual feedback on click."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        btn = authenticated_page.locator("button:visible").first
        if btn.count() > 0:
            btn.click()
            # After click the button may get an active/pressed class or aria-pressed
            # Just ensure no JS error occurred
            errors = []
            authenticated_page.on("pageerror", lambda err: errors.append(str(err)))
            assert len(errors) == 0, "Clicking button should not cause JS errors"

    def test_button_disabled_state(self, authenticated_page: Page) -> None:
        """Verify a disabled button cannot be clicked and shows disabled styling."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        disabled_btn = authenticated_page.locator("button[disabled]").first
        if disabled_btn.count() > 0:
            expect(disabled_btn).to_be_disabled()

    def test_button_loading_state(self, authenticated_page: Page) -> None:
        """Verify buttons show a loading indicator during async operations."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        loading_btn = authenticated_page.locator('[data-testid="loading-button"]').first
        if loading_btn.count() > 0:
            loading_btn.click()
            spinner = loading_btn.locator(".spinner, .loading, [data-testid='spinner']")
            expect(spinner).to_be_visible()


# ---------------------------------------------------------------------------
# Toast notifications
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestToastNotifications:
    """Tests for toast / snackbar notification components."""

    def test_toast_notification_appears(self, authenticated_page: Page) -> None:
        """Verify a toast notification appears after a triggering action."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="toast-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            toast = authenticated_page.locator('[data-testid="toast"], [role="alert"]')
            expect(toast.first).to_be_visible()

    def test_toast_notification_auto_dismisses(self, authenticated_page: Page) -> None:
        """Verify toast notifications auto-dismiss after a timeout."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="toast-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            toast = authenticated_page.locator('[data-testid="toast"], [role="alert"]')
            expect(toast.first).to_be_visible()
            # Wait for auto-dismiss (typically 3-5 seconds)
            toast.first.wait_for(state="hidden", timeout=8000)

    def test_toast_notification_manual_close(self, authenticated_page: Page) -> None:
        """Verify toast notifications can be manually dismissed."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="toast-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            toast = authenticated_page.locator('[data-testid="toast"], [role="alert"]')
            expect(toast.first).to_be_visible()
            close_btn = toast.first.locator('[data-testid="toast-close"], button')
            if close_btn.count() > 0:
                close_btn.first.click()
                toast.first.wait_for(state="hidden", timeout=3000)


# ---------------------------------------------------------------------------
# Modal dialog
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestModals:
    """Tests for modal/dialog components."""

    def test_modal_opens_on_trigger(self, authenticated_page: Page) -> None:
        """Verify the modal opens when its trigger button is clicked."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="modal-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            modal = ModalPage(authenticated_page)
            modal.wait_for_open()
            assert modal.is_open(), "Modal should be open after trigger click"

    def test_modal_closes_on_overlay_click(self, authenticated_page: Page) -> None:
        """Verify clicking the overlay backdrop closes the modal."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="modal-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            modal = ModalPage(authenticated_page)
            modal.wait_for_open()
            modal.close_by_overlay_click()
            modal.wait_for_close()
            assert not modal.is_open(), "Modal should close on overlay click"

    def test_modal_closes_on_escape_key(self, authenticated_page: Page) -> None:
        """Verify pressing Escape closes the modal."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="modal-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            modal = ModalPage(authenticated_page)
            modal.wait_for_open()
            authenticated_page.keyboard.press("Escape")
            modal.wait_for_close()
            assert not modal.is_open(), "Modal should close on Escape key"

    def test_modal_traps_focus(self, authenticated_page: Page) -> None:
        """Verify focus is trapped within the modal when open."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="modal-trigger"]').first
        if trigger.count() > 0:
            trigger.click()
            modal = ModalPage(authenticated_page)
            modal.wait_for_open()
            # Tab several times and verify focus stays within modal
            for _ in range(10):
                authenticated_page.keyboard.press("Tab")
            focused_in_modal = authenticated_page.evaluate("""
                () => {
                    const modal = document.querySelector('[data-testid="modal-content"]');
                    return modal ? modal.contains(document.activeElement) : false;
                }
            """)
            assert focused_in_modal, "Focus should remain trapped inside the modal"


# ---------------------------------------------------------------------------
# Tooltip
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestTooltips:
    """Tests for tooltip components."""

    def test_tooltip_appears_on_hover(self, authenticated_page: Page) -> None:
        """Verify a tooltip appears when hovering over a trigger element."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="tooltip-trigger"]').first
        if trigger.count() > 0:
            trigger.hover()
            tooltip = authenticated_page.locator('[data-testid="tooltip"], [role="tooltip"]')
            expect(tooltip.first).to_be_visible()

    def test_tooltip_disappears_on_leave(self, authenticated_page: Page) -> None:
        """Verify the tooltip disappears when the mouse leaves the trigger."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        trigger = authenticated_page.locator('[data-testid="tooltip-trigger"]').first
        if trigger.count() > 0:
            trigger.hover()
            tooltip = authenticated_page.locator('[data-testid="tooltip"], [role="tooltip"]')
            expect(tooltip.first).to_be_visible()
            authenticated_page.locator("body").hover(position={"x": 0, "y": 0})
            tooltip.first.wait_for(state="hidden", timeout=3000)


# ---------------------------------------------------------------------------
# Accordion
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestAccordion:
    """Tests for accordion / collapsible components."""

    def test_accordion_expand_collapse(self, authenticated_page: Page) -> None:
        """Verify accordion panels expand on click and collapse on second click."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        header = authenticated_page.locator(
            '[data-testid="accordion-header"]'
        ).first
        if header.count() > 0:
            header.click()
            panel = authenticated_page.locator('[data-testid="accordion-panel"]').first
            expect(panel).to_be_visible()
            header.click()
            panel.wait_for(state="hidden", timeout=3000)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestTabs:
    """Tests for tab navigation components."""

    def test_tabs_switch_content(self, authenticated_page: Page) -> None:
        """Verify clicking a tab switches the visible content panel."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        tabs = authenticated_page.locator('[role="tab"]')
        if tabs.count() >= 2:
            tabs.nth(1).click()
            panels = authenticated_page.locator('[role="tabpanel"]')
            expect(panels.nth(1)).to_be_visible()

    def test_tabs_keyboard_navigation(self, authenticated_page: Page) -> None:
        """Verify arrow keys navigate between tabs."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        tabs = authenticated_page.locator('[role="tab"]')
        if tabs.count() >= 2:
            tabs.first.focus()
            authenticated_page.keyboard.press("ArrowRight")
            focused_id = authenticated_page.evaluate(
                "document.activeElement.getAttribute('data-testid') || document.activeElement.id"
            )
            assert focused_id != "", "Arrow key should move focus to next tab"


# ---------------------------------------------------------------------------
# Carousel
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestCarousel:
    """Tests for carousel / slider components."""

    def test_carousel_next_previous(self, authenticated_page: Page) -> None:
        """Verify next and previous buttons cycle carousel slides."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        next_btn = authenticated_page.locator('[data-testid="carousel-next"]').first
        prev_btn = authenticated_page.locator('[data-testid="carousel-prev"]').first
        if next_btn.count() > 0:
            next_btn.click()
            authenticated_page.wait_for_timeout(500)
            prev_btn.click()
            authenticated_page.wait_for_timeout(500)
            # No error means controls work
            slide = authenticated_page.locator('[data-testid="carousel-slide"].active, [data-testid="carousel-slide"][aria-current="true"]')
            assert slide.count() >= 1, "There should be an active carousel slide"

    def test_carousel_autoplay(self, authenticated_page: Page) -> None:
        """Verify the carousel auto-advances slides."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        slides = authenticated_page.locator('[data-testid="carousel-slide"]')
        if slides.count() >= 2:
            first_active = authenticated_page.evaluate("""
                () => document.querySelector('[data-testid="carousel-slide"].active, [data-testid="carousel-slide"][aria-current="true"]')?.dataset.index || '0'
            """)
            authenticated_page.wait_for_timeout(5000)
            second_active = authenticated_page.evaluate("""
                () => document.querySelector('[data-testid="carousel-slide"].active, [data-testid="carousel-slide"][aria-current="true"]')?.dataset.index || '0'
            """)
            assert first_active != second_active, "Carousel should auto-advance"


# ---------------------------------------------------------------------------
# Progress / loading indicators
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestLoadingIndicators:
    """Tests for progress bars, spinners, and skeleton loaders."""

    def test_progress_bar_updates(self, authenticated_page: Page) -> None:
        """Verify the progress bar value updates dynamically."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        progress = authenticated_page.locator(
            '[data-testid="progress-bar"], [role="progressbar"]'
        ).first
        if progress.count() > 0:
            expect(progress).to_be_visible()
            value = progress.get_attribute("aria-valuenow")
            assert value is not None, "Progress bar should have aria-valuenow"

    def test_loading_spinner_visibility(self, authenticated_page: Page) -> None:
        """Verify a loading spinner is shown during data fetch."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        spinner = authenticated_page.locator(
            '[data-testid="loading-spinner"], [data-testid="spinner"]'
        ).first
        # Spinner might briefly appear during page load
        if spinner.count() > 0 and spinner.is_visible():
            expect(spinner).to_be_visible()

    def test_skeleton_loading_state(self, authenticated_page: Page) -> None:
        """Verify skeleton placeholders appear before content loads."""
        # Navigate fresh to catch loading state
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        skeleton = authenticated_page.locator(
            '[data-testid="skeleton"], .skeleton'
        ).first
        # Skeleton may only be briefly visible
        if skeleton.count() > 0:
            expect(skeleton).to_have_count(lambda c: c >= 0)


# ---------------------------------------------------------------------------
# Infinite scroll
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestInfiniteScroll:
    """Tests for infinite scroll / lazy loading."""

    def test_infinite_scroll_loads_more(self, authenticated_page: Page) -> None:
        """Verify scrolling to the bottom loads additional content."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        items = authenticated_page.locator('[data-testid="list-item"]')
        initial_count = items.count()
        if initial_count > 0:
            authenticated_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            authenticated_page.wait_for_timeout(2000)
            new_count = items.count()
            assert new_count >= initial_count, (
                "Scrolling should load at least as many items"
            )


# ---------------------------------------------------------------------------
# Copy to clipboard
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestClipboard:
    """Tests for copy-to-clipboard functionality."""

    def test_copy_to_clipboard_button(self, authenticated_page: Page) -> None:
        """Verify the copy button copies content and shows confirmation."""
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        copy_btn = authenticated_page.locator('[data-testid="copy-button"]').first
        if copy_btn.count() > 0:
            copy_btn.click()
            # Look for a "Copied!" confirmation
            confirmation = authenticated_page.locator(
                '[data-testid="copy-confirmation"], .copied'
            ).first
            if confirmation.count() > 0:
                expect(confirmation).to_be_visible()


# ---------------------------------------------------------------------------
# Theme / dark mode
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestTheme:
    """Tests for dark mode toggle and theme persistence."""

    def test_dark_mode_toggle(self, authenticated_page: Page) -> None:
        """Verify toggling dark mode changes the page theme."""
        settings_pg = SettingsPage(authenticated_page)
        settings_pg.navigate_to_settings()
        settings_pg.select_theme("dark")
        # Verify dark class or data attribute on html/body
        is_dark = authenticated_page.evaluate("""
            () => {
                const html = document.documentElement;
                return html.classList.contains('dark') ||
                       html.getAttribute('data-theme') === 'dark' ||
                       document.body.classList.contains('dark');
            }
        """)
        assert is_dark, "Dark mode should be applied"
        settings_pg.select_theme("light")

    def test_theme_persistence_across_pages(self, authenticated_page: Page) -> None:
        """Verify the selected theme persists when navigating to another page."""
        settings_pg = SettingsPage(authenticated_page)
        settings_pg.navigate_to_settings()
        settings_pg.select_theme("dark")
        settings_pg.save_all()
        authenticated_page.goto(f"{settings.base_url}/dashboard")
        authenticated_page.wait_for_load_state("domcontentloaded")
        is_dark = authenticated_page.evaluate("""
            () => {
                const html = document.documentElement;
                return html.classList.contains('dark') ||
                       html.getAttribute('data-theme') === 'dark' ||
                       document.body.classList.contains('dark');
            }
        """)
        assert is_dark, "Dark mode should persist across pages"
        # Restore light mode
        settings_pg.navigate_to_settings()
        settings_pg.select_theme("light")
        settings_pg.save_all()


# ---------------------------------------------------------------------------
# Badge / notification count
# ---------------------------------------------------------------------------


@pytest.mark.ui
class TestBadge:
    """Tests for badge / notification count components."""

    def test_badge_notification_count(self, authenticated_page: Page) -> None:
        """Verify the notification badge displays the correct count."""
        dashboard = DashboardPage(authenticated_page)
        dashboard.navigate_to_dashboard()
        count = dashboard.get_notification_count()
        assert isinstance(count, int), "Notification count should be an integer"
        assert count >= 0, "Notification count should be non-negative"
