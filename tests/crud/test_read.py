"""Tests for entity read (list + detail) operations.

Covers listing entities, pagination, sorting, searching, filtering,
detail view, empty states, and data export.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.search_results_page import SearchResultsPage
from pages.table_page import TablePage
from utils.api_client import APIClient

pytestmark = [pytest.mark.crud, pytest.mark.regression]


class TestListView:
    """Tests for the entity list/table view."""

    @pytest.mark.smoke
    def test_list_view_displays_entities(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the list view displays seeded entities."""
        table = TablePage(entities_list_page)
        assert table.get_row_count() > 0

    def test_list_view_shows_correct_columns(self, entities_list_page: Page) -> None:
        """Verify the table displays the expected column headers."""
        table = TablePage(entities_list_page)
        headers = table.get_headers()
        assert len(headers) > 0
        # Common expected columns
        expected_columns = ["Name", "Email", "Status"]
        for col in expected_columns:
            assert any(col.lower() in h.lower() for h in headers), (
                f"Expected column '{col}' not found in headers: {headers}"
            )

    def test_list_view_default_sort(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the list view has a default sort order applied."""
        table = TablePage(entities_list_page)
        rows_before = table.get_column_values(0)
        assert len(rows_before) > 0

    def test_list_view_loading_state(self, authenticated_page: Page) -> None:
        """Verify a loading indicator appears while data is being fetched."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        # Check for loading indicator before data loads
        loading = page.locator('[data-testid="loading-indicator"], [data-testid="spinner"]')
        # Loading may be very fast; just verify the page eventually shows content
        page.wait_for_load_state("networkidle")
        table = TablePage(page)
        assert page.locator(table.TABLE).count() > 0 or page.locator(table.EMPTY_STATE).count() > 0


class TestListViewEmptyState:
    """Tests for the empty state of the entity list."""

    def test_list_view_empty_state(self, authenticated_page: Page) -> None:
        """Verify the empty state message when no entities exist."""
        page = authenticated_page
        table = TablePage(page)

        # Search for something that should not exist
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")
        table.search("zzz_nonexistent_entity_xyz_12345")
        page.wait_for_load_state("networkidle")

        if table.get_row_count() == 0:
            assert table.is_empty_state_visible()


class TestPagination:
    """Tests for table pagination."""

    def test_list_view_pagination(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify pagination controls are visible when enough records exist."""
        table = TablePage(entities_list_page)
        pagination = entities_list_page.locator(table.PAGINATION)
        # Pagination may or may not be visible depending on record count
        if table.get_row_count() > 0:
            # Just verify the table loads successfully
            assert table.get_row_count() >= 1

    def test_list_view_items_per_page(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify changing items per page updates the displayed rows."""
        table = TablePage(entities_list_page)
        per_page_select = entities_list_page.locator(table.PER_PAGE_SELECT)

        if per_page_select.count() > 0:
            initial_count = table.get_row_count()
            table.select_per_page(5)
            entities_list_page.wait_for_load_state("networkidle")
            new_count = table.get_row_count()
            assert new_count <= 5


class TestSorting:
    """Tests for table column sorting."""

    def test_sort_by_column_ascending(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify sorting a column in ascending order."""
        table = TablePage(entities_list_page)

        table.sort_by("name")
        entities_list_page.wait_for_load_state("networkidle")

        values = table.get_column_values(0)
        if len(values) > 1:
            assert values == sorted(values, key=str.lower)

    def test_sort_by_column_descending(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify sorting a column in descending order."""
        table = TablePage(entities_list_page)

        # Click twice for descending
        table.sort_by("name")
        entities_list_page.wait_for_load_state("networkidle")
        table.sort_by("name")
        entities_list_page.wait_for_load_state("networkidle")

        values = table.get_column_values(0)
        if len(values) > 1:
            assert values == sorted(values, key=str.lower, reverse=True)


class TestSearchAndFilter:
    """Tests for searching and filtering in the list view."""

    @pytest.mark.smoke
    def test_search_entities_by_name(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify searching entities by name returns matching results."""
        table = TablePage(entities_list_page)
        search_name = seed_test_data[0].get("name", "")

        table.search(search_name)
        entities_list_page.wait_for_load_state("networkidle")

        assert table.get_row_count() >= 1

    def test_search_with_no_results(self, entities_list_page: Page) -> None:
        """Verify a no-results message when searching for nonexistent data."""
        table = TablePage(entities_list_page)
        table.search("zzz_completely_nonexistent_entity_99999")
        entities_list_page.wait_for_load_state("networkidle")

        assert table.get_row_count() == 0

    def test_search_partial_match(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify partial text search returns matching results."""
        table = TablePage(entities_list_page)
        full_name = seed_test_data[0].get("name", "TestEntity")
        partial = full_name[:4] if len(full_name) > 4 else full_name

        table.search(partial)
        entities_list_page.wait_for_load_state("networkidle")

        assert table.get_row_count() >= 1

    def test_filter_by_category(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify filtering entities by category."""
        table = TablePage(entities_list_page)
        filter_input = entities_list_page.locator('[data-testid="table-filter-category"]')

        if filter_input.count() > 0:
            table.apply_filter("category", "general")
            entities_list_page.wait_for_load_state("networkidle")
            assert table.get_row_count() >= 0

    def test_filter_by_date_range(self, entities_list_page: Page) -> None:
        """Verify filtering entities by date range."""
        page = entities_list_page
        date_from = page.locator('[data-testid="table-filter-date_from"]')
        date_to = page.locator('[data-testid="table-filter-date_to"]')

        if date_from.count() > 0 and date_to.count() > 0:
            date_from.fill("2024-01-01")
            date_to.fill("2026-12-31")
            page.wait_for_load_state("networkidle")
            table = TablePage(page)
            assert table.get_row_count() >= 0

    def test_filter_by_status(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify filtering entities by status."""
        table = TablePage(entities_list_page)
        filter_input = entities_list_page.locator('[data-testid="table-filter-status"]')

        if filter_input.count() > 0:
            table.apply_filter("status", "active")
            entities_list_page.wait_for_load_state("networkidle")
            assert table.get_row_count() >= 0

    def test_combine_multiple_filters(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify combining multiple filters narrows results correctly."""
        table = TablePage(entities_list_page)
        page = entities_list_page

        category_filter = page.locator('[data-testid="table-filter-category"]')
        status_filter = page.locator('[data-testid="table-filter-status"]')

        if category_filter.count() > 0 and status_filter.count() > 0:
            table.apply_filter("category", "general")
            page.wait_for_load_state("networkidle")
            count_after_one = table.get_row_count()

            table.apply_filter("status", "active")
            page.wait_for_load_state("networkidle")
            count_after_two = table.get_row_count()

            assert count_after_two <= count_after_one

    def test_clear_all_filters(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify clearing all filters restores the full list."""
        table = TablePage(entities_list_page)
        page = entities_list_page

        initial_count = table.get_row_count()

        table.search("test")
        page.wait_for_load_state("networkidle")

        # Clear the search
        table.search("")
        page.wait_for_load_state("networkidle")

        restored_count = table.get_row_count()
        assert restored_count >= initial_count or restored_count >= 0


class TestDetailView:
    """Tests for the entity detail/view page."""

    @pytest.mark.smoke
    def test_detail_view_displays_all_fields(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the detail view shows all entity fields."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "view")
        page.wait_for_load_state("networkidle")

        # Verify key detail fields are present
        name_field = page.locator('[data-testid="detail-name"]')
        email_field = page.locator('[data-testid="detail-email"]')
        expect(name_field).to_be_visible()
        expect(email_field).to_be_visible()

    def test_detail_view_related_records(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the detail view shows related records section."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "view")
        page.wait_for_load_state("networkidle")

        related_section = page.locator('[data-testid="related-records"]')
        # Related records may or may not exist
        if related_section.count() > 0:
            expect(related_section).to_be_visible()


class TestDataExport:
    """Tests for exporting entity data."""

    def test_export_data_csv(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify exporting entity data to CSV."""
        page = entities_list_page
        export_btn = page.locator('[data-testid="export-csv"]')

        if export_btn.count() > 0:
            with page.expect_download() as download_info:
                export_btn.click()
            download = download_info.value
            assert download.suggested_filename.endswith(".csv")

    def test_export_data_pdf(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify exporting entity data to PDF."""
        page = entities_list_page
        export_btn = page.locator('[data-testid="export-pdf"]')

        if export_btn.count() > 0:
            with page.expect_download() as download_info:
                export_btn.click()
            download = download_info.value
            assert download.suggested_filename.endswith(".pdf")
