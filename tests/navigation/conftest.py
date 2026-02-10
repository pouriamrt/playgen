"""Navigation-specific fixtures for viewport sizes and authenticated contexts."""
from __future__ import annotations

import pytest
from playwright.sync_api import BrowserContext, Page

from config.settings import settings

# Viewport presets used across navigation and responsive tests
VIEWPORT_DESKTOP = {"width": 1920, "height": 1080}
VIEWPORT_TABLET_LANDSCAPE = {"width": 1024, "height": 768}
VIEWPORT_TABLET_PORTRAIT = {"width": 768, "height": 1024}
VIEWPORT_MOBILE = {"width": 375, "height": 667}
VIEWPORT_MOBILE_SMALL = {"width": 320, "height": 568}

ALL_VIEWPORTS = [
    pytest.param(VIEWPORT_DESKTOP, id="desktop-1920"),
    pytest.param(VIEWPORT_TABLET_LANDSCAPE, id="tablet-landscape-1024"),
    pytest.param(VIEWPORT_TABLET_PORTRAIT, id="tablet-portrait-768"),
    pytest.param(VIEWPORT_MOBILE, id="mobile-375"),
    pytest.param(VIEWPORT_MOBILE_SMALL, id="mobile-small-320"),
]

MOBILE_VIEWPORTS = [
    pytest.param(VIEWPORT_MOBILE, id="mobile-375"),
    pytest.param(VIEWPORT_MOBILE_SMALL, id="mobile-small-320"),
]


@pytest.fixture()
def viewport_page(page: Page, request: pytest.FixtureRequest) -> Page:
    """Return a page resized to the viewport specified via indirect parametrize."""
    vp = request.param
    page.set_viewport_size(vp)
    return page


@pytest.fixture()
def nav_authenticated_page(authenticated_page: Page) -> Page:
    """Return an authenticated page already on the dashboard for navigation tests."""
    return authenticated_page


@pytest.fixture()
def mobile_context(context: BrowserContext) -> BrowserContext:
    """Return a browser context configured with mobile viewport."""
    context.pages[0].set_viewport_size(VIEWPORT_MOBILE) if context.pages else None
    return context
