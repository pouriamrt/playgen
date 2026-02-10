from __future__ import annotations

from typing import Any, Generator

import pytest
from playwright.sync_api import APIRequestContext, Playwright

from config.settings import settings


@pytest.fixture(scope="session")
def base_api_url() -> str:
    """Return the base API URL from project settings."""
    return settings.api_url


@pytest.fixture(scope="session")
def api_request_context(playwright: Playwright, base_api_url: str) -> Generator[APIRequestContext, None, None]:
    """Create a Playwright APIRequestContext for direct API testing.

    This context shares no state with the browser and is suitable for
    pure backend verification.
    """
    context = playwright.request.new_context(
        base_url=base_api_url,
        extra_http_headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    yield context
    context.dispose()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """Return authorization headers for authenticated API requests.

    Override this fixture per-module to provide a real token obtained
    via the login flow.
    """
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.fixture(scope="session")
def auth_api_context(
    playwright: Playwright, base_api_url: str
) -> Generator[APIRequestContext, None, None]:
    """Create an authenticated Playwright APIRequestContext.

    Performs a login call to obtain a token, then creates a context
    with that token as a default header.
    """
    # Obtain a token via the login endpoint
    temp_ctx = playwright.request.new_context(base_url=base_api_url)
    login_response = temp_ctx.post(
        "/auth/login",
        data={"email": settings.test_user, "password": settings.test_pass},
    )
    token = ""
    if login_response.ok:
        body = login_response.json()
        token = body.get("token", body.get("access_token", ""))
    temp_ctx.dispose()

    context = playwright.request.new_context(
        base_url=base_api_url,
        extra_http_headers={
            "Authorization": f"Bearer {token}" if token else "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    yield context
    context.dispose()


def response_validator(response: Any, expected_status: int = 200) -> dict:
    """Validate an API response status and return the parsed JSON body.

    Raises AssertionError when the status code does not match.
    """
    assert response.status == expected_status, (
        f"Expected status {expected_status}, got {response.status}. "
        f"Body: {response.text()[:500]}"
    )
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return {}
