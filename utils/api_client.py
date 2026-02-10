from __future__ import annotations

from typing import Any

import requests

from config.settings import settings


class APIClient:
    """REST API client wrapper for backend verification."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or settings.api_url).rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["Accept"] = "application/json"

    def set_auth_token(self, token: str) -> None:
        """Set the authorization bearer token."""
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_auth(self) -> None:
        """Remove authorization header."""
        self.session.headers.pop("Authorization", None)

    def get(self, path: str, params: dict[str, Any] | None = None) -> requests.Response:
        """Send a GET request."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.get(url, params=params, timeout=settings.default_timeout / 1000)
        return response

    def post(self, path: str, data: dict[str, Any] | None = None) -> requests.Response:
        """Send a POST request with JSON body."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.post(url, json=data, timeout=settings.default_timeout / 1000)
        return response

    def put(self, path: str, data: dict[str, Any] | None = None) -> requests.Response:
        """Send a PUT request with JSON body."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.put(url, json=data, timeout=settings.default_timeout / 1000)
        return response

    def patch(self, path: str, data: dict[str, Any] | None = None) -> requests.Response:
        """Send a PATCH request with JSON body."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.patch(url, json=data, timeout=settings.default_timeout / 1000)
        return response

    def delete(self, path: str) -> requests.Response:
        """Send a DELETE request."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.delete(url, timeout=settings.default_timeout / 1000)
        return response

    def assert_status(self, response: requests.Response, expected: int) -> None:
        """Assert that the response has the expected status code."""
        assert response.status_code == expected, (
            f"Expected status {expected}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )

    def assert_json_key(self, response: requests.Response, key: str) -> Any:
        """Assert a key exists in the JSON response and return its value."""
        data = response.json()
        assert key in data, f"Key '{key}' not found in response: {list(data.keys())}"
        return data[key]
