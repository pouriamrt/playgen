from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class DashboardPage(BasePage):
    """Page Object for the Dashboard page."""

    # Selectors
    WELCOME_MESSAGE = '[data-testid="welcome-message"]'
    STATS_CARDS = '[data-testid="stats-card"]'
    RECENT_ACTIVITY = '[data-testid="recent-activity"]'
    ACTIVITY_ITEMS = '[data-testid="activity-item"]'
    QUICK_ACTIONS = '[data-testid="quick-actions"]'
    NOTIFICATIONS_BELL = '[data-testid="notifications-bell"]'
    NOTIFICATION_COUNT = '[data-testid="notification-count"]'
    USER_MENU = '[data-testid="user-menu"]'
    USER_MENU_DROPDOWN = '[data-testid="user-menu-dropdown"]'
    SIDEBAR_NAV = '[data-testid="sidebar-nav"]'
    SIDEBAR_ITEM_TEMPLATE = '[data-testid="sidebar-item-{item}"]'
    CHARTS_WIDGET = '[data-testid="charts-widget"]'
    QUICK_ACTION_TEMPLATE = '[data-testid="quick-action-{action}"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.path = "/dashboard"

    def navigate_to_dashboard(self) -> None:
        """Navigate to the dashboard page."""
        self.navigate(self.path)

    def get_welcome_text(self) -> str:
        """Return the welcome message text."""
        return self.get_text(self.WELCOME_MESSAGE)

    def get_stats(self) -> list[str]:
        """Return the text content of all stats cards."""
        cards = self.page.locator(self.STATS_CARDS)
        return [cards.nth(i).inner_text() for i in range(cards.count())]

    def get_stats_count(self) -> int:
        """Return how many stats cards are displayed."""
        return self.get_element_count(self.STATS_CARDS)

    def get_recent_activity(self) -> list[str]:
        """Return the text of each recent activity item."""
        items = self.page.locator(self.ACTIVITY_ITEMS)
        return [items.nth(i).inner_text() for i in range(items.count())]

    def click_quick_action(self, action: str) -> None:
        """Click a quick-action button by name."""
        selector = self.QUICK_ACTION_TEMPLATE.format(action=action)
        self.click(selector)

    def get_notification_count(self) -> int:
        """Return the number shown on the notification bell badge."""
        if not self.is_visible(self.NOTIFICATION_COUNT):
            return 0
        text = self.get_text(self.NOTIFICATION_COUNT)
        return int(text) if text.isdigit() else 0

    def click_notifications(self) -> None:
        """Click the notifications bell."""
        self.click(self.NOTIFICATIONS_BELL)

    def open_user_menu(self) -> None:
        """Open the user menu dropdown."""
        self.click(self.USER_MENU)
        self.wait_for_selector(self.USER_MENU_DROPDOWN)

    def is_user_menu_open(self) -> bool:
        """Check if the user menu dropdown is visible."""
        return self.is_visible(self.USER_MENU_DROPDOWN)

    def navigate_sidebar(self, item: str) -> None:
        """Click a sidebar navigation item."""
        selector = self.SIDEBAR_ITEM_TEMPLATE.format(item=item)
        self.click(selector)

    def is_charts_widget_visible(self) -> bool:
        """Check if the charts widget is rendered."""
        return self.is_visible(self.CHARTS_WIDGET)
