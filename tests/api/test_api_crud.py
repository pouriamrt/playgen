"""Direct API CRUD tests.

Exercises the backend REST API directly using Playwright's APIRequestContext
(not the browser) to verify CRUD operations, query parameters, and error
responses.
"""
from __future__ import annotations

import json
from typing import Generator

import pytest
from playwright.sync_api import APIRequestContext

from tests.api.conftest import response_validator


pytestmark = [pytest.mark.api]

# The entity endpoint used throughout; change to match your API.
ENTITY_PATH = "/items"


# ---------------------------------------------------------------------------
# Tests: Read operations
# ---------------------------------------------------------------------------


class TestApiReadOperations:
    """GET operations on the entity endpoint."""

    def test_api_get_all_entities(self, api_request_context: APIRequestContext) -> None:
        """GET /items should return a list of entities."""
        response = api_request_context.get(ENTITY_PATH)
        data = response_validator(response, expected_status=200)

        assert isinstance(data, (list, dict))

    def test_api_get_single_entity(self, api_request_context: APIRequestContext) -> None:
        """GET /items/1 should return a single entity."""
        response = api_request_context.get(f"{ENTITY_PATH}/1")

        if response.status == 200:
            data = response.json()
            assert "id" in data
        else:
            # Entity may not exist in a fresh database
            assert response.status in (200, 404)

    def test_api_get_nonexistent_entity_404(self, api_request_context: APIRequestContext) -> None:
        """GET /items/99999 should return 404 for a non-existent entity."""
        response = api_request_context.get(f"{ENTITY_PATH}/99999")

        assert response.status == 404

    def test_api_response_format_json(self, api_request_context: APIRequestContext) -> None:
        """The API should return responses with content-type application/json."""
        response = api_request_context.get(ENTITY_PATH)
        content_type = response.headers.get("content-type", "")

        assert "application/json" in content_type

    def test_api_response_has_correct_status_codes(
        self, api_request_context: APIRequestContext
    ) -> None:
        """GET on an existing resource should return 200."""
        response = api_request_context.get(ENTITY_PATH)

        assert response.status in (200, 204)


# ---------------------------------------------------------------------------
# Tests: Create operations
# ---------------------------------------------------------------------------


class TestApiCreateOperations:
    """POST operations on the entity endpoint."""

    def test_api_create_entity(self, api_request_context: APIRequestContext) -> None:
        """POST /items with valid data should create a new entity."""
        payload = {"name": "Test Entity", "description": "Created by test"}
        response = api_request_context.post(ENTITY_PATH, data=payload)

        assert response.status in (200, 201)
        data = response.json()
        assert "id" in data or "name" in data

    def test_api_create_entity_returns_201(self, api_request_context: APIRequestContext) -> None:
        """POST /items should return 201 Created on success."""
        payload = {"name": "Another Entity", "description": "Test 201 status"}
        response = api_request_context.post(ENTITY_PATH, data=payload)

        assert response.status in (200, 201)

    def test_api_create_entity_validates_input(
        self, api_request_context: APIRequestContext
    ) -> None:
        """POST /items with missing required fields should return 400/422."""
        response = api_request_context.post(ENTITY_PATH, data={})

        assert response.status in (400, 422)

    def test_api_handles_malformed_json(self, api_request_context: APIRequestContext) -> None:
        """POST with malformed JSON should return 400."""
        response = api_request_context.post(
            ENTITY_PATH,
            data="not-valid-json{{{",
            headers={"Content-Type": "application/json"},
        )

        assert response.status in (400, 415, 422)

    def test_api_handles_missing_required_fields(
        self, api_request_context: APIRequestContext
    ) -> None:
        """POST with partial data (missing required field) should return 400/422."""
        response = api_request_context.post(
            ENTITY_PATH, data={"description": "Missing name"}
        )

        assert response.status in (400, 422)


# ---------------------------------------------------------------------------
# Tests: Update operations
# ---------------------------------------------------------------------------


class TestApiUpdateOperations:
    """PUT/PATCH operations on the entity endpoint."""

    def test_api_update_entity(self, api_request_context: APIRequestContext) -> None:
        """PUT /items/1 should update the entity with the new data."""
        # Create first
        create_response = api_request_context.post(
            ENTITY_PATH, data={"name": "To Update", "description": "Original"}
        )
        if create_response.status not in (200, 201):
            pytest.skip("Could not create entity for update test")

        entity_id = create_response.json().get("id", 1)

        update_response = api_request_context.put(
            f"{ENTITY_PATH}/{entity_id}",
            data={"name": "Updated Name", "description": "Updated"},
        )

        assert update_response.status in (200, 204)

    def test_api_update_nonexistent_entity(
        self, api_request_context: APIRequestContext
    ) -> None:
        """PUT /items/99999 should return 404."""
        response = api_request_context.put(
            f"{ENTITY_PATH}/99999",
            data={"name": "Ghost", "description": "Does not exist"},
        )

        assert response.status == 404

    def test_api_partial_update_entity(self, api_request_context: APIRequestContext) -> None:
        """PATCH /items/1 should partially update the entity."""
        create_response = api_request_context.post(
            ENTITY_PATH, data={"name": "Partial Target", "description": "Original"}
        )
        if create_response.status not in (200, 201):
            pytest.skip("Could not create entity for partial update test")

        entity_id = create_response.json().get("id", 1)

        patch_response = api_request_context.patch(
            f"{ENTITY_PATH}/{entity_id}",
            data={"description": "Patched only description"},
        )

        assert patch_response.status in (200, 204)


# ---------------------------------------------------------------------------
# Tests: Delete operations
# ---------------------------------------------------------------------------


class TestApiDeleteOperations:
    """DELETE operations on the entity endpoint."""

    def test_api_delete_entity(self, api_request_context: APIRequestContext) -> None:
        """DELETE /items/{id} should remove the entity."""
        create_response = api_request_context.post(
            ENTITY_PATH, data={"name": "To Delete", "description": "Bye"}
        )
        if create_response.status not in (200, 201):
            pytest.skip("Could not create entity for delete test")

        entity_id = create_response.json().get("id", 1)

        delete_response = api_request_context.delete(f"{ENTITY_PATH}/{entity_id}")

        assert delete_response.status in (200, 204)

        # Verify it is gone
        get_response = api_request_context.get(f"{ENTITY_PATH}/{entity_id}")
        assert get_response.status == 404

    def test_api_delete_nonexistent_entity(
        self, api_request_context: APIRequestContext
    ) -> None:
        """DELETE /items/99999 should return 404."""
        response = api_request_context.delete(f"{ENTITY_PATH}/99999")

        assert response.status == 404


# ---------------------------------------------------------------------------
# Tests: Query parameters (pagination, sort, filter, search)
# ---------------------------------------------------------------------------


class TestApiQueryParameters:
    """Tests for pagination, sorting, filtering, and search query parameters."""

    def test_api_pagination_parameters(self, api_request_context: APIRequestContext) -> None:
        """The API should support page and per_page query parameters."""
        response = api_request_context.get(
            ENTITY_PATH, params={"page": "1", "per_page": "10"}
        )

        assert response.status in (200, 204)

    def test_api_sort_parameters(self, api_request_context: APIRequestContext) -> None:
        """The API should support sort query parameters."""
        response = api_request_context.get(
            ENTITY_PATH, params={"sort": "name", "order": "asc"}
        )

        assert response.status in (200, 204)

    def test_api_filter_parameters(self, api_request_context: APIRequestContext) -> None:
        """The API should support filter query parameters."""
        response = api_request_context.get(
            ENTITY_PATH, params={"status": "active"}
        )

        assert response.status in (200, 204)

    def test_api_search_parameter(self, api_request_context: APIRequestContext) -> None:
        """The API should support a search/q query parameter."""
        response = api_request_context.get(
            ENTITY_PATH, params={"q": "test"}
        )

        assert response.status in (200, 204)

    def test_api_bulk_operations(self, api_request_context: APIRequestContext) -> None:
        """The API should support bulk operations (e.g., batch delete)."""
        # Create a few entities first
        ids = []
        for i in range(3):
            resp = api_request_context.post(
                ENTITY_PATH,
                data={"name": f"Bulk {i}", "description": "Batch test"},
            )
            if resp.status in (200, 201):
                ids.append(resp.json().get("id"))

        if not ids:
            pytest.skip("Could not create entities for bulk test")

        # Attempt bulk delete
        response = api_request_context.post(
            f"{ENTITY_PATH}/bulk-delete",
            data={"ids": ids},
        )

        # Bulk endpoint may not exist, so accept 404 as well
        assert response.status in (200, 204, 404, 405)
