from __future__ import annotations

from typing import Any, Generator

import pytest
from faker import Faker
from playwright.sync_api import Page

from config.settings import settings
from utils.api_client import APIClient

fake = Faker()


# ---------------------------------------------------------------------------
# Authenticated page fixture (CRUD-specific)
# ---------------------------------------------------------------------------


@pytest.fixture()
def authenticated_page(page: Page) -> Page:
    """Return a page logged in as the standard test user for CRUD tests."""
    page.goto(f"{settings.base_url}/login")
    page.fill('[data-testid="username-input"]', settings.test_user)
    page.fill('[data-testid="password-input"]', settings.test_pass)
    page.click('[data-testid="login-button"]')
    page.wait_for_url("**/dashboard**")
    return page


# ---------------------------------------------------------------------------
# API client with authentication
# ---------------------------------------------------------------------------


@pytest.fixture()
def auth_api_client() -> Generator[APIClient, None, None]:
    """Provide an authenticated API client for backend verification."""
    client = APIClient()
    response = client.post("/auth/login", data={
        "email": settings.test_user,
        "password": settings.test_pass,
    })
    if response.status_code == 200:
        token = response.json().get("token", "")
        client.set_auth_token(token)
    yield client
    client.session.close()


# ---------------------------------------------------------------------------
# Sample entity data factory
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_entity_data() -> dict[str, Any]:
    """Generate sample entity data for CRUD operations."""
    return {
        "name": fake.company(),
        "description": fake.paragraph(nb_sentences=2),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "status": "active",
        "category": "general",
        "address": fake.address(),
        "website": fake.url(),
    }


@pytest.fixture()
def sample_entity_factory():
    """Factory fixture to generate multiple unique entity data dicts."""

    def _create(**overrides: Any) -> dict[str, Any]:
        data = {
            "name": fake.company(),
            "description": fake.paragraph(nb_sentences=2),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "status": "active",
            "category": "general",
        }
        data.update(overrides)
        return data

    return _create


# ---------------------------------------------------------------------------
# Seed test data via API
# ---------------------------------------------------------------------------


@pytest.fixture()
def seed_test_data(auth_api_client: APIClient, sample_entity_factory) -> Generator[list[dict], None, None]:
    """Create test records via the API and clean them up afterward."""
    created_ids: list[str] = []
    records: list[dict] = []

    for _ in range(5):
        data = sample_entity_factory()
        response = auth_api_client.post("/entities", data=data)
        if response.status_code in (200, 201):
            record = response.json()
            created_ids.append(str(record.get("id", "")))
            records.append(record)

    yield records

    # Cleanup: delete seeded records
    for entity_id in created_ids:
        if entity_id:
            auth_api_client.delete(f"/entities/{entity_id}")


# ---------------------------------------------------------------------------
# Cleanup test data
# ---------------------------------------------------------------------------


@pytest.fixture()
def cleanup_test_data(auth_api_client: APIClient):
    """Fixture that collects entity IDs during a test and deletes them after."""
    created_ids: list[str] = []

    class Collector:
        def add(self, entity_id: str) -> None:
            created_ids.append(entity_id)

    collector = Collector()
    yield collector

    for entity_id in created_ids:
        if entity_id:
            auth_api_client.delete(f"/entities/{entity_id}")


# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------


@pytest.fixture()
def entities_list_page(authenticated_page: Page) -> Page:
    """Navigate to the entities list page and return the page."""
    authenticated_page.goto(f"{settings.base_url}/entities")
    authenticated_page.wait_for_load_state("networkidle")
    return authenticated_page
