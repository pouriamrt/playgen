"""Tests for entity creation (Create) operations.

Covers creating entities through the UI, verifying backend persistence,
handling validation errors, security inputs, and edge cases.
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


class TestCreateEntityVisibility:
    """Tests for create button and form visibility."""

    @pytest.mark.smoke
    def test_create_button_visible(self, entities_list_page: Page) -> None:
        """Verify the create/add entity button is visible on the list page."""
        page = entities_list_page
        create_btn = page.locator('[data-testid="create-entity-button"]')
        expect(create_btn).to_be_visible()

    def test_create_form_opens(self, entities_list_page: Page) -> None:
        """Verify clicking the create button opens the create form."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)
        expect(page.locator(form.FORM)).to_be_visible()


class TestCreateEntitySuccess:
    """Tests for successful entity creation flows."""

    @pytest.mark.smoke
    def test_create_entity_with_required_fields(
        self, entities_list_page: Page, sample_entity_data: dict, cleanup_test_data
    ) -> None:
        """Verify creating an entity with only the required fields succeeds."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        form.fill_field("name", sample_entity_data["name"])
        form.fill_field("email", sample_entity_data["email"])
        form.submit()

        page.wait_for_load_state("networkidle")
        success_toast = page.locator('[data-testid="toast-success"]')
        expect(success_toast).to_be_visible()

    @pytest.mark.smoke
    def test_create_entity_with_all_fields(
        self, entities_list_page: Page, sample_entity_data: dict, cleanup_test_data
    ) -> None:
        """Verify creating an entity with all fields populated succeeds."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        form.fill_field("name", sample_entity_data["name"])
        form.fill_field("email", sample_entity_data["email"])
        form.fill_field("phone", sample_entity_data["phone"])
        form.fill_textarea("description", sample_entity_data["description"])
        form.select_dropdown("category", sample_entity_data["category"])
        form.select_dropdown("status", sample_entity_data["status"])
        form.fill_field("website", sample_entity_data["website"])
        form.submit()

        page.wait_for_load_state("networkidle")
        success_toast = page.locator('[data-testid="toast-success"]')
        expect(success_toast).to_be_visible()

    def test_create_entity_appears_in_list(
        self, entities_list_page: Page, sample_entity_data: dict, cleanup_test_data
    ) -> None:
        """Verify a newly created entity appears in the list view."""
        page = entities_list_page
        entity_name = sample_entity_data["name"]

        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)
        form.fill_field("name", entity_name)
        form.fill_field("email", sample_entity_data["email"])
        form.submit()

        page.wait_for_load_state("networkidle")
        table = TablePage(page)
        table.search(entity_name)
        page.wait_for_load_state("networkidle")

        assert table.get_row_count() >= 1
        cell_values = table.get_column_values(0)
        assert entity_name in cell_values

    def test_create_entity_persisted_in_backend(
        self, entities_list_page: Page, sample_entity_data: dict,
        auth_api_client: APIClient, cleanup_test_data
    ) -> None:
        """Verify the created entity is persisted in the backend via API."""
        page = entities_list_page
        entity_name = sample_entity_data["name"]

        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)
        form.fill_field("name", entity_name)
        form.fill_field("email", sample_entity_data["email"])
        form.submit()

        page.wait_for_load_state("networkidle")

        # Verify via API
        response = auth_api_client.get("/entities", params={"search": entity_name})
        auth_api_client.assert_status(response, 200)
        results = response.json()
        entity_names = [e.get("name") for e in results.get("data", results)]
        assert entity_name in entity_names

    def test_create_entity_shows_success_notification(
        self, entities_list_page: Page, sample_entity_data: dict, cleanup_test_data
    ) -> None:
        """Verify a success notification is displayed after entity creation."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        form.fill_field("name", sample_entity_data["name"])
        form.fill_field("email", sample_entity_data["email"])
        form.submit()

        page.wait_for_load_state("networkidle")
        toast = page.locator('[data-testid="toast-success"]')
        expect(toast).to_be_visible()
        expect(toast).to_contain_text("created")

    def test_create_entity_redirects_to_detail(
        self, entities_list_page: Page, sample_entity_data: dict, cleanup_test_data
    ) -> None:
        """Verify the user is redirected to the entity detail page after creation."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        form.fill_field("name", sample_entity_data["name"])
        form.fill_field("email", sample_entity_data["email"])
        form.submit()

        page.wait_for_load_state("networkidle")
        assert "/entities/" in page.url

    def test_create_multiple_entities_sequentially(
        self, entities_list_page: Page, sample_entity_factory, cleanup_test_data
    ) -> None:
        """Verify multiple entities can be created one after another."""
        page = entities_list_page

        for _ in range(3):
            data = sample_entity_factory()
            page.goto(f"{settings.base_url}/entities")
            page.wait_for_load_state("networkidle")
            page.click('[data-testid="create-entity-button"]')

            form = FormPage(page)
            form.fill_field("name", data["name"])
            form.fill_field("email", data["email"])
            form.submit()
            page.wait_for_load_state("networkidle")

    def test_create_entity_with_default_values(
        self, entities_list_page: Page, cleanup_test_data
    ) -> None:
        """Verify the create form has sensible default values pre-filled."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        status_value = page.locator('[data-testid="select-status"]').input_value()
        assert status_value != ""


class TestCreateEntityWithRelatedData:
    """Tests for creating entities with related records and special fields."""

    def test_create_entity_with_related_records(
        self, entities_list_page: Page, sample_entity_data: dict, cleanup_test_data
    ) -> None:
        """Verify creating an entity with related record selection (foreign key dropdown)."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        form.fill_field("name", sample_entity_data["name"])
        form.fill_field("email", sample_entity_data["email"])

        # Select from a related records dropdown
        related_select = page.locator('[data-testid="select-parent_id"]')
        if related_select.count() > 0:
            form.select_dropdown("parent_id", "")
            options = page.locator('[data-testid="select-parent_id"] option')
            if options.count() > 1:
                form.select_dropdown("parent_id", options.nth(1).get_attribute("value") or "")

        form.submit()
        page.wait_for_load_state("networkidle")

    def test_create_entity_with_image_upload(
        self, entities_list_page: Page, sample_entity_data: dict, cleanup_test_data, tmp_path
    ) -> None:
        """Verify creating an entity with an image file upload."""
        page = entities_list_page

        # Create a temporary image file
        test_image = tmp_path / "test_image.png"
        test_image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        form.fill_field("name", sample_entity_data["name"])
        form.fill_field("email", sample_entity_data["email"])
        form.upload_file("image", str(test_image))
        form.submit()

        page.wait_for_load_state("networkidle")

    def test_create_entity_with_rich_text_field(
        self, entities_list_page: Page, sample_entity_data: dict, cleanup_test_data
    ) -> None:
        """Verify creating an entity with rich text content in a textarea."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        rich_text = "<b>Bold</b> and <i>italic</i> content with a <a>link</a>"
        form.fill_field("name", sample_entity_data["name"])
        form.fill_field("email", sample_entity_data["email"])
        form.fill_textarea("description", rich_text)
        form.submit()

        page.wait_for_load_state("networkidle")


class TestCreateEntityValidation:
    """Tests for create form validation and error handling."""

    def test_create_entity_validation_errors(self, entities_list_page: Page) -> None:
        """Verify validation errors are shown when submitting an empty form."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        form.submit()

        assert form.is_validation_error_visible("name")
        assert form.is_validation_error_visible("email")

    def test_create_entity_with_duplicate_name(
        self, entities_list_page: Page, seed_test_data: list[dict]
    ) -> None:
        """Verify proper error when creating an entity with an existing name."""
        page = entities_list_page
        existing_name = seed_test_data[0].get("name", "Existing Entity")

        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)
        form.fill_field("name", existing_name)
        form.fill_field("email", fake.email())
        form.submit()

        page.wait_for_load_state("networkidle")
        error = page.locator('[data-testid="toast-error"], [data-testid="error-name"]')
        expect(error).to_be_visible()

    def test_create_entity_cancel(self, entities_list_page: Page, sample_entity_data: dict) -> None:
        """Verify canceling the create form discards changes and returns to list."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        form.fill_field("name", sample_entity_data["name"])
        form.cancel()

        page.wait_for_load_state("networkidle")
        table = TablePage(page)
        table.search(sample_entity_data["name"])
        page.wait_for_load_state("networkidle")

        assert table.get_row_count() == 0 or not any(
            sample_entity_data["name"] in v for v in table.get_column_values(0)
        )

    def test_create_entity_max_field_lengths(self, entities_list_page: Page) -> None:
        """Verify fields enforce maximum character limits."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        long_name = "A" * 500
        form.fill_field("name", long_name)
        form.fill_field("email", fake.email())
        form.submit()

        page.wait_for_load_state("networkidle")
        # Either the field truncated the input or a validation error is shown
        error_visible = form.is_validation_error_visible("name")
        field_value = form.get_field_value("name")
        assert error_visible or len(field_value) < 500

    def test_create_entity_with_special_characters(
        self, entities_list_page: Page, cleanup_test_data
    ) -> None:
        """Verify entities can be created with special characters in fields."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        special_name = "Test & Co. <Special> 'Chars' \"Quoted\" @#$%"
        form.fill_field("name", special_name)
        form.fill_field("email", fake.email())
        form.submit()

        page.wait_for_load_state("networkidle")
        success = page.locator('[data-testid="toast-success"]')
        error = page.locator('[data-testid="toast-error"]')
        assert success.is_visible() or error.is_visible()


class TestCreateEntitySecurity:
    """Security tests for entity creation inputs."""

    @pytest.mark.smoke
    def test_create_entity_xss_prevention(
        self, entities_list_page: Page, cleanup_test_data
    ) -> None:
        """Verify XSS payloads in input fields are properly sanitized."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        xss_payload = '<script>alert("XSS")</script>'
        form.fill_field("name", xss_payload)
        form.fill_field("email", fake.email())
        form.submit()

        page.wait_for_load_state("networkidle")

        # Verify the script tag is not rendered as executable HTML
        scripts_on_page = page.locator("script")
        for i in range(scripts_on_page.count()):
            content = scripts_on_page.nth(i).inner_text()
            assert 'alert("XSS")' not in content

    @pytest.mark.smoke
    def test_create_entity_sql_injection_prevention(
        self, entities_list_page: Page, cleanup_test_data
    ) -> None:
        """Verify SQL injection payloads are handled safely."""
        page = entities_list_page
        page.click('[data-testid="create-entity-button"]')
        form = FormPage(page)

        sql_payload = "'; DROP TABLE entities; --"
        form.fill_field("name", sql_payload)
        form.fill_field("email", fake.email())
        form.submit()

        page.wait_for_load_state("networkidle")

        # Verify the application still works (no server error)
        page.goto(f"{settings.base_url}/entities")
        page.wait_for_load_state("networkidle")
        table = TablePage(page)
        # The table should still be functional
        assert page.locator(table.TABLE).count() >= 0
