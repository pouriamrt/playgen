"""Tests-level conftest with shared test fixtures.

This conftest supplements the root conftest.py with fixtures
that are specific to the test modules. The root conftest handles
browser setup, authentication pages, and screenshot-on-failure.
"""

from __future__ import annotations

import pytest
from faker import Faker

from utils.helpers import generate_fake_user, random_email


fake = Faker()


@pytest.fixture()
def fake_user() -> dict[str, str]:
    """Generate a fake user with random data for test isolation."""
    return generate_fake_user()


@pytest.fixture()
def unique_email() -> str:
    """Generate a unique email address for test isolation."""
    return random_email()


@pytest.fixture()
def sample_text() -> str:
    """Generate sample text for form inputs."""
    return fake.paragraph(nb_sentences=2)
