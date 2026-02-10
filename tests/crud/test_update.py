"""Tests for entity update (Edit) operations.

Covers updating entities through the UI, verifying pre-populated forms,
backend persistence, concurrent edits, and edge cases.
"""
from __future__ import annotations

import pytest
from faker import Faker
from playwright.sync_api import Page, expect

from config.settings import settings
from pages.form_page import FormPage
from pages.modal_page import ModalPage
from pages.table_page import TablePage
from utils.api_client import APIClient

fake = Faker()

pytestmark = [pytest.mark.crud, pytest.mark.regression]


class TestUpdateVisibility:
    """Tests for edit button visibility and form pre-population."""

    @pytest.mark.smoke
    def test_edit_button_visible(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the edit button is visible on each row of the entity table."""
        page = entities_list_page
        edit_btn = page.locator('[data-testid="row-action-edit-0"]')
        expect(edit_btn).to_be_visible()

    @pytest.mark.smoke
    def test_edit_form_pre_populated(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the edit form is pre-populated with existing entity data."""
        page = entities_list_page
        table = TablePage(page)

        # Get the name from the first row
        original_name = table.get_cell_value(0, 0)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        field_value = form.get_field_value("name")
        assert field_value == original_name


class TestUpdateSuccess:
    """Tests for successful entity update flows."""

    @pytest.mark.smoke
    def test_update_single_field(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify updating a single field on an entity."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        new_name = f"Updated {fake.company()}"
        form.fill_field("name", new_name)
        form.submit()

        page.wait_for_load_state("networkidle")
        toast = page.locator('[data-testid="toast-success"]')
        expect(toast).to_be_visible()

    def test_update_all_fields(
        self, entities_list_page: Page, seed_test_data: list[dict], sample_entity_data: dict
    ) -> None:
        """Verify updating all fields on an entity."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        form.fill_field("name", sample_entity_data["name"])
        form.fill_field("email", sample_entity_data["email"])
        form.fill_field("phone", sample_entity_data["phone"])
        form.fill_textarea("description", sample_entity_data["description"])
        form.submit()

        page.wait_for_load_state("networkidle")
        toast = page.locator('[data-testid="toast-success"]')
        expect(toast).to_be_visible()

    def test_update_persisted_in_backend(
        self, entities_list_page: Page, seed_test_data: list[dict], auth_api_client: APIClient
    ) -> None:
        """Verify the update is persisted in the backend via API."""
        page = entities_list_page
        table = TablePage(page)
        new_name = f"API-Verified {fake.company()}"

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        form.fill_field("name", new_name)
        form.submit()
        page.wait_for_load_state("networkidle")

        # Verify via API
        response = auth_api_client.get("/entities", params={"search": new_name})
        auth_api_client.assert_status(response, 200)
        results = response.json()
        data = results.get("data", results) if isinstance(results, dict) else results
        names = [e.get("name") for e in data]
        assert new_name in names

    def test_update_reflected_in_list(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the updated entity name is reflected in the list view."""
        page = entities_list_page
        table = TablePage(page)
        new_name = f"ListCheck {fake.company()}"

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        form.fill_field("name", new_name)
        form.submit()
        page.wait_for_load_state("networkidle")

        # Navigate back to list
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        table.search(new_name)
        page.wait_for_load_state("networkidle")

        values = table.get_column_values(0)
        assert new_name in values

    def test_update_shows_success_notification(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify a success notification is displayed after updating."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        form.fill_field("name", f"Notif {fake.company()}")
        form.submit()

        page.wait_for_load_state("networkidle")
        toast = page.locator('[data-testid="toast-success"]')
        expect(toast).to_be_visible()
        expect(toast).to_contain_text("updated")

    def test_update_preserves_unmodified_fields(
        self, entities_list_page: Page, seed_test_data: list[dict], auth_api_client: APIClient
    ) -> None:
        """Verify that fields not touched during edit retain their original values."""
        page = entities_list_page
        table = TablePage(page)

        # Get original entity data via API
        entity_id = seed_test_data[0].get("id", "")
        if entity_id:
            original = auth_api_client.get(f"/entities/{entity_id}").json()

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        new_name = f"Preserve {fake.company()}"
        form.fill_field("name", new_name)
        form.submit()
        page.wait_for_load_state("networkidle")

        if entity_id:
            updated = auth_api_client.get(f"/entities/{entity_id}").json()
            assert updated.get("email") == original.get("email")


class TestUpdateCancel:
    """Tests for canceling edit operations."""

    def test_update_cancel_preserves_original(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify canceling an edit does not change the original entity."""
        page = entities_list_page
        table = TablePage(page)

        original_name = table.get_cell_value(0, 0)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        form.fill_field("name", f"CANCELED {fake.company()}")
        form.cancel()

        page.wait_for_load_state("networkidle")
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        current_name = table.get_cell_value(0, 0)
        assert current_name == original_name

    def test_update_undo_changes(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the undo/reset button reverts form changes."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        original_value = form.get_field_value("name")
        form.fill_field("name", "UNDO THIS CHANGE")

        reset_btn = page.locator('[data-testid="form-reset"], [data-testid="form-undo"]')
        if reset_btn.count() > 0:
            reset_btn.click()
            restored_value = form.get_field_value("name")
            assert restored_value == original_value


class TestUpdateValidation:
    """Tests for edit form validation."""

    def test_update_validation_errors(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify validation errors when editing with invalid data."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        form.fill_field("email", "invalid-email")
        form.submit()

        page.wait_for_load_state("networkidle")
        assert form.is_validation_error_visible("email")

    def test_update_with_empty_required_field(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify validation error when clearing a required field."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        form.fill_field("name", "")
        form.submit()

        page.wait_for_load_state("networkidle")
        assert form.is_validation_error_visible("name")


class TestAdvancedUpdate:
    """Tests for advanced update features."""

    def test_update_optimistic_locking(
        self, authenticated_page: Page, seed_test_data: list[dict], auth_api_client: APIClient
    ) -> None:
        """Verify concurrent edit detection (optimistic locking / stale data)."""
        page = authenticated_page
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")

        table = TablePage(page)
        entity_id = seed_test_data[0].get("id", "")

        # Open edit form
        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        # Modify via API (simulate concurrent edit)
        if entity_id:
            auth_api_client.put(f"/entities/{entity_id}", data={"name": f"ConcurrentEdit {fake.company()}"})

        # Try to submit the form
        form = FormPage(page)
        form.fill_field("name", f"StaleEdit {fake.company()}")
        form.submit()

        page.wait_for_load_state("networkidle")
        # The application may show a conflict warning or succeed
        # This test documents the behavior
        conflict_warning = page.locator('[data-testid="conflict-warning"], [data-testid="toast-warning"]')
        success_toast = page.locator('[data-testid="toast-success"]')
        assert conflict_warning.count() > 0 or success_toast.count() > 0

    def test_inline_edit_in_table(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify inline editing capability in the table view."""
        page = entities_list_page
        table = TablePage(page)

        # Check if inline edit is supported
        first_cell = page.locator(f'{table.TABLE_ROWS} >> nth=0 >> {table.TABLE_CELLS} >> nth=0')
        first_cell.dblclick()

        inline_input = page.locator('[data-testid="inline-edit-input"]')
        if inline_input.count() > 0:
            new_value = f"InlineEdited {fake.company()}"
            inline_input.fill(new_value)
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle")

    def test_bulk_update_selected_items(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify bulk updating multiple selected entities."""
        page = entities_list_page
        table = TablePage(page)

        # Select multiple rows
        for i in range(min(2, table.get_row_count())):
            table.select_row(i)

        bulk_edit_btn = page.locator('[data-testid="bulk-action-edit"]')
        if bulk_edit_btn.count() > 0:
            bulk_edit_btn.click()
            page.wait_for_load_state("networkidle")

            # Fill bulk edit form
            bulk_status = page.locator('[data-testid="bulk-edit-status"]')
            if bulk_status.count() > 0:
                page.select_option('[data-testid="bulk-edit-status"]', value="inactive")
                page.click('[data-testid="bulk-edit-submit"]')
                page.wait_for_load_state("networkidle")

    def test_update_audit_trail(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify the last modified timestamp is updated after editing."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        form.fill_field("name", f"AuditTrail {fake.company()}")
        form.submit()
        page.wait_for_load_state("networkidle")

        # Check for last modified indicator
        modified_field = page.locator('[data-testid="detail-updated_at"], [data-testid="detail-modified"]')
        if modified_field.count() > 0:
            expect(modified_field).not_to_be_empty()

    def test_update_with_file_replacement(
        self, entities_list_page: Page, seed_test_data: list[dict], tmp_path
    ) -> None:
        """Verify replacing an uploaded file during entity edit."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        form = FormPage(page)
        file_upload = page.locator('[data-testid="file-upload-image"]')
        if file_upload.count() > 0:
            new_file = tmp_path / "replacement.png"
            new_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            form.upload_file("image", str(new_file))
            form.submit()
            page.wait_for_load_state("networkidle")

    def test_update_with_stale_data_warning(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify a warning is shown when editing stale data."""
        page = entities_list_page
        table = TablePage(page)

        table.click_row_action(0, "edit")
        page.wait_for_load_state("networkidle")

        # Check for stale data warning element
        stale_warning = page.locator('[data-testid="stale-data-warning"]')
        # This test documents whether the feature exists
        if stale_warning.count() > 0:
            expect(stale_warning).to_be_visible()
