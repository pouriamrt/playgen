from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class SearchResultsPage(BasePage):
    """Page Object for the Search Results page."""

    # Selectors
    SEARCH_INPUT = '[data-testid="search-input"]'
    SEARCH_SUBMIT = '[data-testid="search-submit"]'
    RESULTS_LIST = '[data-testid="results-list"]'
    RESULT_ITEMS = '[data-testid="result-item"]'
    RESULT_ITEM_TEMPLATE = '[data-testid="result-item-{index}"]'
    NO_RESULTS_MESSAGE = '[data-testid="no-results"]'
    FILTERS_SIDEBAR = '[data-testid="filters-sidebar"]'
    FILTER_TEMPLATE = '[data-testid="filter-{category}-{value}"]'
    ACTIVE_FILTERS = '[data-testid="active-filter"]'
    REMOVE_FILTER_TEMPLATE = '[data-testid="remove-filter-{name}"]'
    SORT_DROPDOWN = '[data-testid="sort-dropdown"]'
    RESULT_COUNT = '[data-testid="result-count"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.path = "/search"

    def navigate_to_search(self) -> None:
        """Navigate to the search page."""
        self.navigate(self.path)

    def search(self, query: str) -> None:
        """Enter a search query and submit."""
        self.fill(self.SEARCH_INPUT, query)
        self.click(self.SEARCH_SUBMIT)

    def get_result_count(self) -> int:
        """Return the number of result items displayed."""
        return self.page.locator(self.RESULT_ITEMS).count()

    def get_result_count_text(self) -> str:
        """Return the text of the result count indicator."""
        return self.get_text(self.RESULT_COUNT)

    def get_results(self) -> list[str]:
        """Return the text content of all result items."""
        items = self.page.locator(self.RESULT_ITEMS)
        return [items.nth(i).inner_text() for i in range(items.count())]

    def click_result(self, index: int) -> None:
        """Click a result item by index (0-based)."""
        self.page.locator(self.RESULT_ITEMS).nth(index).click()

    def apply_filter(self, category: str, value: str) -> None:
        """Apply a filter by category and value."""
        selector = self.FILTER_TEMPLATE.format(category=category, value=value)
        self.click(selector)

    def remove_filter(self, name: str) -> None:
        """Remove an active filter by name."""
        selector = self.REMOVE_FILTER_TEMPLATE.format(name=name)
        self.click(selector)

    def get_active_filters(self) -> list[str]:
        """Return the text of all active filter chips."""
        filters = self.page.locator(self.ACTIVE_FILTERS)
        return [filters.nth(i).inner_text() for i in range(filters.count())]

    def sort_by(self, option: str) -> None:
        """Select a sort option from the sort dropdown."""
        self.select_option(self.SORT_DROPDOWN, value=option)

    def get_no_results_message(self) -> str:
        """Return the no-results message text."""
        return self.get_text(self.NO_RESULTS_MESSAGE)

    def is_no_results_visible(self) -> bool:
        """Check if the no-results message is displayed."""
        return self.is_visible(self.NO_RESULTS_MESSAGE)

    def is_filters_sidebar_visible(self) -> bool:
        """Check if the filters sidebar is visible."""
        return self.is_visible(self.FILTERS_SIDEBAR)
