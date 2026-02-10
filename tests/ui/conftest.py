"""UI-specific fixtures for component testing, accessibility, and visual regression."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from config.settings import settings


@pytest.fixture()
def dashboard_page(authenticated_page: Page) -> Page:
    """Return an authenticated page navigated to the dashboard."""
    authenticated_page.goto(f"{settings.base_url}/dashboard")
    authenticated_page.wait_for_load_state("domcontentloaded")
    return authenticated_page


@pytest.fixture()
def settings_page(authenticated_page: Page) -> Page:
    """Return an authenticated page navigated to settings."""
    authenticated_page.goto(f"{settings.base_url}/settings")
    authenticated_page.wait_for_load_state("domcontentloaded")
    return authenticated_page


@pytest.fixture()
def form_page(authenticated_page: Page) -> Page:
    """Return an authenticated page navigated to a form."""
    authenticated_page.goto(f"{settings.base_url}/form")
    authenticated_page.wait_for_load_state("domcontentloaded")
    return authenticated_page
