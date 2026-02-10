from __future__ import annotations

from playwright.sync_api import Page

from pages.base_page import BasePage


class TablePage(BasePage):
    """Page Object for data table / grid components."""

    # Selectors
    TABLE = '[data-testid="data-table"]'
    TABLE_HEADERS = '[data-testid="table-header"]'
    TABLE_ROWS = '[data-testid="table-row"]'
    TABLE_CELLS = '[data-testid="table-cell"]'
    SORT_ICON_TEMPLATE = '[data-testid="sort-{column}"]'
    PAGINATION = '[data-testid="pagination"]'
    PAGE_BUTTON_TEMPLATE = '[data-testid="page-{number}"]'
    NEXT_PAGE = '[data-testid="next-page"]'
    PREV_PAGE = '[data-testid="prev-page"]'
    SEARCH_INPUT = '[data-testid="table-search"]'
    FILTER_INPUT_TEMPLATE = '[data-testid="table-filter-{name}"]'
    BULK_SELECT_ALL = '[data-testid="bulk-select-all"]'
    ROW_CHECKBOX_TEMPLATE = '[data-testid="row-checkbox-{index}"]'
    ROW_ACTION_TEMPLATE = '[data-testid="row-action-{action}-{row}"]'
    PER_PAGE_SELECT = '[data-testid="per-page-select"]'
    EMPTY_STATE = '[data-testid="empty-state"]'
    ROW_COUNT_DISPLAY = '[data-testid="row-count"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def get_row_count(self) -> int:
        """Return the number of rows in the table."""
        return self.page.locator(self.TABLE_ROWS).count()

    def get_headers(self) -> list[str]:
        """Return a list of all table header texts."""
        headers = self.page.locator(self.TABLE_HEADERS)
        return [headers.nth(i).inner_text() for i in range(headers.count())]

    def get_cell_value(self, row: int, col: int) -> str:
        """Get the text content of a specific cell (0-indexed row, col)."""
        row_locator = self.page.locator(self.TABLE_ROWS).nth(row)
        cell_locator = row_locator.locator(self.TABLE_CELLS).nth(col)
        return cell_locator.inner_text()

    def get_column_values(self, col: int) -> list[str]:
        """Return all values in a specific column (0-indexed)."""
        rows = self.page.locator(self.TABLE_ROWS)
        values = []
        for i in range(rows.count()):
            cell = rows.nth(i).locator(self.TABLE_CELLS).nth(col)
            values.append(cell.inner_text())
        return values

    def sort_by(self, column: str) -> None:
        """Click the sort icon for a column."""
        selector = self.SORT_ICON_TEMPLATE.format(column=column)
        self.click(selector)

    def is_sorted_by(self, column: str, direction: str = "asc") -> bool:
        """Check if the table is sorted by a column in the given direction."""
        selector = self.SORT_ICON_TEMPLATE.format(column=column)
        sort_attr = self.get_attribute(selector, "aria-sort")
        if direction == "asc":
            return sort_attr == "ascending"
        return sort_attr == "descending"

    def search(self, query: str) -> None:
        """Type a search query into the table search box."""
        self.fill(self.SEARCH_INPUT, query)

    def apply_filter(self, name: str, value: str) -> None:
        """Apply a filter value to a named filter input."""
        selector = self.FILTER_INPUT_TEMPLATE.format(name=name)
        self.fill(selector, value)

    def go_to_page(self, page_number: int) -> None:
        """Navigate to a specific pagination page."""
        selector = self.PAGE_BUTTON_TEMPLATE.format(number=page_number)
        self.click(selector)

    def go_to_next_page(self) -> None:
        """Click the next-page button."""
        self.click(self.NEXT_PAGE)

    def go_to_prev_page(self) -> None:
        """Click the previous-page button."""
        self.click(self.PREV_PAGE)

    def select_per_page(self, count: int) -> None:
        """Select how many items to display per page."""
        self.select_option(self.PER_PAGE_SELECT, value=str(count))

    def select_row(self, index: int) -> None:
        """Check the checkbox for a specific row (0-indexed)."""
        selector = self.ROW_CHECKBOX_TEMPLATE.format(index=index)
        self.check(selector)

    def select_all_rows(self) -> None:
        """Check the bulk select-all checkbox."""
        self.check(self.BULK_SELECT_ALL)

    def click_row_action(self, row: int, action: str) -> None:
        """Click an action button (edit/delete/view) on a row."""
        selector = self.ROW_ACTION_TEMPLATE.format(action=action, row=row)
        self.click(selector)

    def bulk_action(self, action: str) -> None:
        """Execute a bulk action on selected rows."""
        selector = f'[data-testid="bulk-action-{action}"]'
        self.click(selector)

    def is_empty_state_visible(self) -> bool:
        """Check if the empty-state message is displayed."""
        return self.is_visible(self.EMPTY_STATE)

    def get_displayed_row_count_text(self) -> str:
        """Return the displayed row count text (e.g. 'Showing 1-10 of 50')."""
        return self.get_text(self.ROW_COUNT_DISPLAY)
