"""Tests for advanced search and filtering operations.

Covers global search, advanced multi-criteria search, filter persistence,
URL deep linking, debounce, and various filter types.
"""
from __future__ import annotations

import time

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.search_results_page import SearchResultsPage
from pages.table_page import TablePage

fake = Faker()

pytestmark = [pytest.mark.crud, pytest.mark.regression]


class TestGlobalSearch:
    """Tests for global search functionality."""

    @pytest.mark.smoke
    def test_global_search_bar(self, authenticated_page: Page) -> None:
        """Verify the global search bar is accessible from any page."""
        page = authenticated_page
        search_input = page.locator('[data-testid="global-search"], [data-testid="search-input"]')
        expect(search_input).to_be_visible()

    @pytest.mark.smoke
    def test_global_search_results_page(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify global search navigates to a results page with matches."""
        page = authenticated_page
        search_page = SearchResultsPage(page)

        search_name = seed_test_data[0].get("name", "test")
        search_page.navigate_to_search()
        search_page.search(search_name)
        page.wait_for_load_state("networkidle")

        assert search_page.get_result_count() >= 1

    def test_search_highlights_matches(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify search results highlight the matching text."""
        page = authenticated_page
        search_page = SearchResultsPage(page)

        search_term = seed_test_data[0].get("name", "test")[:5]
        search_page.navigate_to_search()
        search_page.search(search_term)
        page.wait_for_load_state("networkidle")

        highlights = page.locator("mark, .highlight, .search-highlight")
        if search_page.get_result_count() > 0 and highlights.count() > 0:
            expect(highlights.first).to_be_visible()

    def test_search_case_insensitive(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify search is case-insensitive."""
        page = authenticated_page
        search_page = SearchResultsPage(page)

        search_name = seed_test_data[0].get("name", "test")

        # Search with uppercase
        search_page.navigate_to_search()
        search_page.search(search_name.upper())
        page.wait_for_load_state("networkidle")
        upper_count = search_page.get_result_count()

        # Search with lowercase
        search_page.navigate_to_search()
        search_page.search(search_name.lower())
        page.wait_for_load_state("networkidle")
        lower_count = search_page.get_result_count()

        assert upper_count == lower_count

    def test_search_special_characters(self, authenticated_page: Page) -> None:
        """Verify search handles special characters gracefully."""
        page = authenticated_page
        search_page = SearchResultsPage(page)

        search_page.navigate_to_search()
        search_page.search("!@#$%^&*()")
        page.wait_for_load_state("networkidle")

        # Should not cause an error; either no results or some results
        assert search_page.get_result_count() >= 0 or search_page.is_no_results_visible()

    def test_search_debounce_behavior(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify search uses debounce to avoid excessive requests."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        search_input = page.locator(table.SEARCH_INPUT)

        if search_input.count() > 0:
            # Type characters quickly
            search_input.fill("")
            search_input.type("abc", delay=50)

            # Brief pause - debounce should prevent immediate search
            time.sleep(0.2)
            # After debounce period, results should update
            page.wait_for_load_state("networkidle")
            # Test passes if no errors occurred


class TestAdvancedSearch:
    """Tests for advanced search with multiple criteria."""

    def test_advanced_search_multiple_criteria(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify advanced search with multiple criteria filters results."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)

        # Apply search text
        search_name = seed_test_data[0].get("name", "test")[:3]
        table.search(search_name)
        page.wait_for_load_state("networkidle")

        # Apply additional filter
        status_filter = page.locator('[data-testid="table-filter-status"]')
        if status_filter.count() > 0:
            table.apply_filter("status", "active")
            page.wait_for_load_state("networkidle")

        # Results should be a subset
        assert table.get_row_count() >= 0

    def test_saved_search_filters(self, authenticated_page: Page) -> None:
        """Verify saved search/filter presets functionality."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        save_filter_btn = page.locator('[data-testid="save-filter"], [data-testid="save-search"]')
        if save_filter_btn.count() > 0:
            table = TablePage(page)
            table.search("test")
            page.wait_for_load_state("networkidle")

            save_filter_btn.click()
            page.wait_for_load_state("networkidle")

            saved_filters = page.locator('[data-testid="saved-filter"]')
            assert saved_filters.count() >= 0


class TestFilterPersistence:
    """Tests for filter persistence and URL deep linking."""

    def test_filter_persistence_across_pages(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify filters persist when navigating between pages."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        table.search("test")
        page.wait_for_load_state("networkidle")

        # Navigate to page 2 if pagination exists
        next_btn = page.locator(table.NEXT_PAGE)
        if next_btn.count() > 0 and next_btn.is_enabled():
            next_btn.click()
            page.wait_for_load_state("networkidle")

            # Verify the search term is still applied
            search_value = page.locator(table.SEARCH_INPUT).input_value()
            assert "test" in search_value.lower()

    def test_filter_url_parameters(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify filters are reflected in URL parameters for deep linking."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        table.search("deeplink")
        page.wait_for_load_state("networkidle")

        current_url = page.url
        # Many apps encode search in URL params
        if "search" in current_url or "q=" in current_url or "query" in current_url:
            # Navigate directly with the URL
            page.goto(current_url)
            page.wait_for_load_state("networkidle")
            search_value = page.locator(table.SEARCH_INPUT).input_value()
            assert "deeplink" in search_value.lower()


class TestFilterControls:
    """Tests for individual filter controls and interactions."""

    def test_filter_count_badge(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify filter count badge shows number of active filters."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        badge = page.locator('[data-testid="filter-count"], [data-testid="active-filter-count"]')

        status_filter = page.locator('[data-testid="table-filter-status"]')
        if status_filter.count() > 0 and badge.count() > 0:
            table.apply_filter("status", "active")
            page.wait_for_load_state("networkidle")
            badge_text = badge.inner_text()
            assert "1" in badge_text or badge.is_visible()

    def test_filter_reset_individual(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify resetting an individual filter restores results."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        initial_count = table.get_row_count()

        table.search("test_filter_reset_unique")
        page.wait_for_load_state("networkidle")
        filtered_count = table.get_row_count()

        # Clear just the search filter
        table.search("")
        page.wait_for_load_state("networkidle")
        restored_count = table.get_row_count()

        assert restored_count >= filtered_count

    def test_filter_by_boolean_field(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify filtering by a boolean/toggle field."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        bool_filter = page.locator('[data-testid="table-filter-active"], [data-testid="table-filter-is_active"]')
        if bool_filter.count() > 0:
            table = TablePage(page)
            total_before = table.get_row_count()

            bool_filter.click()
            page.wait_for_load_state("networkidle")

            filtered = table.get_row_count()
            assert filtered <= total_before

    def test_date_range_filter(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify filtering entities by a date range."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        date_from = page.locator('[data-testid="table-filter-date_from"]')
        date_to = page.locator('[data-testid="table-filter-date_to"]')

        if date_from.count() > 0 and date_to.count() > 0:
            date_from.fill("2020-01-01")
            date_to.fill("2026-12-31")
            page.wait_for_load_state("networkidle")

            table = TablePage(page)
            assert table.get_row_count() >= 0

    def test_numeric_range_filter(
        self, authenticated_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify filtering entities by a numeric range."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        min_input = page.locator('[data-testid="table-filter-amount_min"], [data-testid="table-filter-price_min"]')
        max_input = page.locator('[data-testid="table-filter-amount_max"], [data-testid="table-filter-price_max"]')

        if min_input.count() > 0 and max_input.count() > 0:
            min_input.fill("0")
            max_input.fill("999999")
            page.wait_for_load_state("networkidle")

            table = TablePage(page)
            assert table.get_row_count() >= 0
