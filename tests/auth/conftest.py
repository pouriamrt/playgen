"""Auth-specific fixtures for authentication and authorization tests."""
from __future__ import annotations

from typing import Generator

import pytest
from faker import Faker
from playwright.sync_api import BrowserContext, Page

from config.settings import settings
from pages.login_page import LoginPage
from utils.api_client import APIClient
from utils.helpers import random_email, random_string

fake = Faker()

# ---------------------------------------------------------------------------
# Credential fixtures
# ---------------------------------------------------------------------------

TEST_USER_CREDENTIALS = {
    "email": settings.test_user,
    "password": settings.test_pass,
}

ADMIN_USER_CREDENTIALS = {
    "email": settings.admin_user,
    "password": settings.admin_pass,
}


@pytest.fixture()
def test_user() -> dict[str, str]:
    """Return standard test user credentials."""
    return TEST_USER_CREDENTIALS.copy()


@pytest.fixture()
def admin_user() -> dict[str, str]:
    """Return admin user credentials."""
    return ADMIN_USER_CREDENTIALS.copy()


@pytest.fixture()
def fresh_user() -> dict[str, str]:
    """Generate a fresh unique user for each test.

    Returns a dict with first_name, last_name, email, password,
    and confirm_password fields suitable for registration.
    """
    password = f"Test{random_string(6)}!1"
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": random_email(),
        "password": password,
        "confirm_password": password,
    }


# ---------------------------------------------------------------------------
# Pre-authenticated page fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def logged_in_page(page: Page) -> Page:
    """Return a page pre-authenticated as the standard test user."""
    login_page = LoginPage(page)
    login_page.navigate_to_login()
    login_page.login(settings.test_user, settings.test_pass)
    page.wait_for_url("**/dashboard**")
    return page


@pytest.fixture()
def admin_logged_in_page(page: Page) -> Page:
    """Return a page pre-authenticated as the admin user."""
    login_page = LoginPage(page)
    login_page.navigate_to_login()
    login_page.login(settings.admin_user, settings.admin_pass)
    page.wait_for_url("**/dashboard**")
    return page


# ---------------------------------------------------------------------------
# Cleanup fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def cleanup_test_users(api_client: APIClient) -> Generator[list[str], None, None]:
    """Collect emails of users created during tests and delete them afterwards."""
    created_emails: list[str] = []
    yield created_emails
    for email in created_emails:
        try:
            api_client.delete(f"/users?email={email}")
        except Exception:
            pass
