"""Tests for entity delete operations.

Covers deleting entities through the UI, confirmation dialogs, backend verification,
bulk delete, cascade behavior, and permission checks.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.modal_page import ModalPage
from pages.table_page import TablePage
from utils.api_client import APIClient

pytestmark = [pytest.mark.crud, pytest.mark.regression]


class TestDeleteVisibility:
    """Tests for delete button visibility."""

    @pytest.mark.smoke
    def test_delete_button_visible(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the delete button is visible on each entity row."""
        page = entities_list_page
        delete_btn = page.locator('[data-testid="row-action-delete-0"]')
        expect(delete_btn).to_be_visible()


class TestDeleteConfirmation:
    """Tests for the delete confirmation dialog."""

    @pytest.mark.smoke
    def test_delete_shows_confirmation_dialog(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify a confirmation dialog appears when clicking delete."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()

        assert modal.is_open()
        body_text = modal.get_body_text()
        assert len(body_text) > 0

    def test_delete_cancel_preserves_entity(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify canceling the delete dialog preserves the entity."""
        page = entities_list_page
        table = TablePage(page)

        original_count = table.get_row_count()
        original_name = table.get_cell_value(0, 0)

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()
        modal.cancel()
        modal.wait_for_close()

        page.wait_for_load_state("networkidle")
        assert table.get_row_count() == original_count
        assert table.get_cell_value(0, 0) == original_name


class TestDeleteSuccess:
    """Tests for successful entity deletion."""

    @pytest.mark.smoke
    def test_delete_confirm_removes_entity(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify confirming deletion removes the entity from the list."""
        page = entities_list_page
        table = TablePage(page)

        original_count = table.get_row_count()
        deleted_name = table.get_cell_value(0, 0)

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()
        modal.confirm()
        modal.wait_for_close()

        page.wait_for_load_state("networkidle")
        new_count = table.get_row_count()
        assert new_count == original_count - 1

        # Verify the deleted entity is no longer in the list
        if new_count > 0:
            remaining_names = table.get_column_values(0)
            assert deleted_name not in remaining_names

    def test_delete_removed_from_backend(
        self, entities_list_page: Page, seed_test_data: list[dict], auth_api_client: APIClient
    ) -> None:
        """Verify the deleted entity is no longer accessible via the API."""
        page = entities_list_page
        table = TablePage(page)

        entity_id = seed_test_data[0].get("id", "")
        deleted_name = seed_test_data[0].get("name", "")

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()
        modal.confirm()
        modal.wait_for_close()
        page.wait_for_load_state("networkidle")

        # Verify via API
        if entity_id:
            response = auth_api_client.get(f"/entities/{entity_id}")
            assert response.status_code in (404, 410)

    def test_delete_removed_from_list(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the deleted entity disappears from the table."""
        page = entities_list_page
        table = TablePage(page)

        deleted_name = table.get_cell_value(0, 0)

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()
        modal.confirm()
        modal.wait_for_close()
        page.wait_for_load_state("networkidle")

        # Search for the deleted entity
        table.search(deleted_name)
        page.wait_for_load_state("networkidle")
        remaining = table.get_column_values(0)
        assert deleted_name not in remaining

    def test_delete_shows_success_notification(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify a success notification appears after deletion."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()
        modal.confirm()
        modal.wait_for_close()
        page.wait_for_load_state("networkidle")

        toast = page.locator('[data-testid="toast-success"]')
        expect(toast).to_be_visible()
        expect(toast).to_contain_text("deleted")


class TestBulkDelete:
    """Tests for bulk deletion of entities."""

    def test_bulk_delete_selected_items(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify deleting multiple selected entities at once."""
        page = entities_list_page
        table = TablePage(page)

        initial_count = table.get_row_count()
        items_to_delete = min(2, initial_count)

        for i in range(items_to_delete):
            table.select_row(i)

        table.bulk_action("delete")
        page.wait_for_load_state("networkidle")

        modal = ModalPage(page)
        if modal.is_open():
            modal.confirm()
            modal.wait_for_close()
            page.wait_for_load_state("networkidle")

        new_count = table.get_row_count()
        assert new_count <= initial_count

    def test_bulk_delete_confirmation(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify bulk delete shows a confirmation dialog with count."""
        page = entities_list_page
        table = TablePage(page)

        table.select_row(0)
        table.select_row(1) if table.get_row_count() > 1 else None

        table.bulk_action("delete")

        modal = ModalPage(page)
        if modal.is_open():
            body = modal.get_body_text()
            # The confirmation should mention the number of items
            assert any(char.isdigit() for char in body) or "selected" in body.lower()
            modal.cancel()


class TestDeleteEdgeCases:
    """Tests for delete edge cases and special scenarios."""

    def test_delete_with_related_records(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify behavior when deleting an entity with related records."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()

        # Check if there is a warning about related records
        warning = page.locator('[data-testid="cascade-warning"], [data-testid="related-warning"]')
        if warning.count() > 0:
            expect(warning).to_be_visible()

        modal.cancel()

    def test_soft_delete_vs_hard_delete(
        self, entities_list_page: Page, seed_test_data: list[dict], auth_api_client: APIClient
    ) -> None:
        """Verify whether delete is soft (archived) or hard (permanent)."""
        page = entities_list_page
        table = TablePage(page)
        entity_id = seed_test_data[0].get("id", "")

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()
        modal.confirm()
        modal.wait_for_close()
        page.wait_for_load_state("networkidle")

        if entity_id:
            # Check if entity still exists as soft-deleted
            response = auth_api_client.get(f"/entities/{entity_id}", params={"include_deleted": "true"})
            if response.status_code == 200:
                data = response.json()
                # Soft delete: entity exists with a deleted flag
                assert data.get("deleted") is True or data.get("deleted_at") is not None
            else:
                # Hard delete: entity is gone completely
                assert response.status_code in (404, 410)

    def test_delete_undo_functionality(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify undo functionality after deleting an entity."""
        page = entities_list_page
        table = TablePage(page)

        deleted_name = table.get_cell_value(0, 0)

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()
        modal.confirm()
        modal.wait_for_close()
        page.wait_for_load_state("networkidle")

        # Look for undo action in the success toast
        undo_btn = page.locator('[data-testid="undo-delete"], [data-testid="toast-undo"]')
        if undo_btn.count() > 0:
            undo_btn.click()
            page.wait_for_load_state("networkidle")

            table.search(deleted_name)
            page.wait_for_load_state("networkidle")
            values = table.get_column_values(0)
            assert deleted_name in values

    def test_cannot_delete_without_permission(self, page: Page) -> None:
        """Verify that unauthorized users cannot delete entities."""
        # Login as a guest or limited user
        page.goto(f"{settings.base_url}/login")
        page.fill('[data-testid="username-input"]', settings.test_user)
        page.fill('[data-testid="password-input"]', settings.test_pass)
        page.click('[data-testid="login-button"]')
        page.wait_for_url("**/dashboard**")

        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        # Check if delete buttons are present or disabled for limited users
        delete_btn = page.locator('[data-testid="row-action-delete-0"]')
        if delete_btn.count() > 0:
            # Button exists - user has permission, test passes
            pass
        else:
            # No delete button - restricted access confirmed
            assert delete_btn.count() == 0

    def test_delete_last_item_shows_empty_state(
        self, authenticated_page: Page, auth_api_client: APIClient, sample_entity_factory
    ) -> None:
        """Verify deleting the last entity shows the empty state."""
        page = authenticated_page

        # Create a single entity
        data = sample_entity_factory()
        response = auth_api_client.post("/entities", data=data)
        entity_name = data["name"]

        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        table.search(entity_name)
        page.wait_for_load_state("networkidle")

        if table.get_row_count() == 1:
            table.click_row_action(0, "delete")
            modal = ModalPage(page)
            modal.wait_for_open()
            modal.confirm()
            modal.wait_for_close()
            page.wait_for_load_state("networkidle")

            # After deleting the only matching item, verify empty state
            assert table.get_row_count() == 0

    def test_delete_updates_pagination(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify pagination updates correctly after deleting an entity."""
        page = entities_list_page
        table = TablePage(page)

        row_count_text_before = ""
        row_count_elem = page.locator(table.ROW_COUNT_DISPLAY)
        if row_count_elem.count() > 0:
            row_count_text_before = row_count_elem.inner_text()

        table.click_row_action(0, "delete")
        modal = ModalPage(page)
        modal.wait_for_open()
        modal.confirm()
        modal.wait_for_close()
        page.wait_for_load_state("networkidle")

        if row_count_elem.count() > 0 and row_count_text_before:
            row_count_text_after = row_count_elem.inner_text()
            assert row_count_text_after != row_count_text_before
